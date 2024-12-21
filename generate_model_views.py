import open3d as o3d
import numpy as np
import os
from django.conf import settings
from django.shortcuts import render
from PIL import Image
import torch
from transformers import GLPNImageProcessor, GLPNForDepthEstimation
import cv2
import requests
from io import BytesIO


# Load and preprocess the image
def load_image(image_path):
    print(f"Loading image: {image_path}")
    try:
        # Validate that image_path is not None
        if not image_path:
            raise ValueError("Image path is missing.")

        # If the image path is a URL, download the image
        if image_path.startswith("http://") or image_path.startswith("https://"):
            response = requests.get(image_path, stream=True)
            response.raise_for_status()

            # Check if the response contains an image
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                raise ValueError(f"URL does not point to a valid image. Content-Type: {content_type}")

            image = Image.open(BytesIO(response.content)).convert("RGB")
        else:
            # Handle local file paths if necessary
            image = Image.open(image_path).convert("RGB")

        print("Image loaded successfully.")
        return image
    
    except Exception as e:
        raise ValueError(f"Failed to load image. Ensure it's a valid image file. Error: {e}")


# Flip the image and depth map for back view generation
def flip_image_and_depth(input_image, depth_map):
    print("Flipping image and depth map for back view...")
    flipped_image = input_image.transpose(Image.FLIP_LEFT_RIGHT)
    flipped_depth = np.flip(depth_map, axis=1)  # Horizontal flip
    flipped_depth = np.abs(flipped_depth - flipped_depth.max())  # Invert depth
    print("Image and depth map flipped successfully.")
    return flipped_image, flipped_depth


# Segment the object in the image using OpenCV GrabCut
def segment_image(input_image):
    print("Segmenting the image using OpenCV GrabCut...")
    image = np.array(input_image)
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    rect = (10, 10, image.shape[1] - 20, image.shape[0] - 20)  # Rough rectangle for segmentation

    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(image, mask, rect, bg_model, fg_model, 5, cv2.GC_INIT_WITH_RECT)

    # Refine mask using morphological operations
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    mask = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')  # Create binary mask
    segmented_image = image * mask[:, :, None]
    print("Image segmentation completed.")
    return Image.fromarray(segmented_image), mask


# Estimate depth map using GLPN
def estimate_depth(input_image, processor, model):
    print("Estimating depth map...")
    inputs = processor(images=input_image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    print("Depth map estimation completed.")
    return outputs.predicted_depth.squeeze().cpu().numpy()


# Refine the depth map with smoothing
def refine_depth_map(depth_map):
    print("Refining the depth map...")
    depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-8)
    smoothed = cv2.bilateralFilter((depth_map * 255).astype('uint8'), d=5, sigmaColor=50, sigmaSpace=50)
    smoothed = cv2.GaussianBlur(smoothed, (9, 9), 0)
    print("Depth map refinement completed.")
    return smoothed / 255.0

def fill_depth_holes(depth_map):
    print("Filling holes in the depth map...")
    depth_map = (depth_map * 255).astype(np.uint8)
    mask = (depth_map == 0).astype(np.uint8)
    filled_depth = cv2.inpaint(depth_map, mask, 3, cv2.INPAINT_TELEA)
    return filled_depth / 255.0

def create_point_cloud(input_image, depth_map, width, height):
    print("Creating point cloud from image and depth map...")
    
     # Resize depth map to match input image size
    depth_resized = cv2.resize(depth_map, (width, height), interpolation=cv2.INTER_NEAREST)
    
    # Mask out areas where depth is invalid (e.g., close to zero)
    depth_resized[depth_resized < 0.01] = 0  # Set a minimum depth threshold
    
    depth_image = (depth_resized * 255 / np.max(depth_resized)).astype('uint8')
    input_image_array = np.array(input_image)

    # Mask black regions in the RGB image
    mask = (input_image_array.sum(axis=2) > 30).astype(np.uint8)  # Exclude near-black regions
    input_image_array[mask == 0] = 0
    depth_image[mask == 0] = 0
    
    rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
        o3d.geometry.Image(input_image_array),
        o3d.geometry.Image(depth_image),
        convert_rgb_to_intensity=False
    )
    camera_intrinsic = o3d.camera.PinholeCameraIntrinsic(width, height, width, height, width / 2, height / 2)
    point_cloud = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, camera_intrinsic)
    
    print(f"Point cloud created with {len(point_cloud.points)} points.")
    return point_cloud


# Combine and align the front and back point clouds
def align_and_combine_point_clouds(front_cloud, back_cloud):
    print("Aligning and combining front and back point clouds...")
    front_points = np.asarray(front_cloud.points)
    back_points = np.asarray(back_cloud.points)

    # Flip back points symmetrically along X-axis
    back_points[:, 0] = -back_points[:, 0]
    
    # Scale back points to match front point cloud size
    scale_factor = 1.0
    back_points *= scale_factor
    
    # Center back points relative to the front points
    back_center = np.mean(back_points, axis=0)
    front_center = np.mean(front_points, axis=0)
    back_points = back_points - back_center + front_center
    
    back_cloud.points = o3d.utility.Vector3dVector(back_points)
    
    # Combine the two clouds
    combined_cloud = front_cloud + back_cloud
    combined_cloud.estimate_normals()
    combined_cloud, _ = combined_cloud.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    
    print(f"Combined point cloud has {len(combined_cloud.points)} points.")
    return combined_cloud


# Create mesh from combined point cloud
def create_mesh(point_cloud):
    print("Creating mesh using Poisson surface reconstruction...")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(point_cloud, depth=14)
    densities = np.asarray(densities)
    density_threshold = np.quantile(densities, 0.05)
    mesh.remove_vertices_by_mask(densities < density_threshold)
    print("Applying Taubin smoothing to the mesh...")
    mesh = mesh.filter_smooth_taubin(number_of_iterations=10)
    print("Mesh creation completed.")
    mesh.compute_vertex_normals()
    return mesh


# Save the mesh to a file
def save_mesh(mesh, output_path):
    print(f"Saving mesh to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    o3d.io.write_triangle_mesh(output_path, mesh)
    print("Mesh saved successfully.")


# Main function to generate the 3D model
def generate_model(request):
    try:
        image_path = request.GET.get('image_path')
        
        input_image = load_image(image_path)
        segmented_image, _ = segment_image(input_image)

        # Depth estimation
        processor = GLPNImageProcessor.from_pretrained("vinvino02/glpn-nyu")
        model = GLPNForDepthEstimation.from_pretrained("vinvino02/glpn-nyu")
        depth_map = fill_depth_holes(refine_depth_map(estimate_depth(segmented_image, processor, model)))

        # Point cloud generation
        width, height = segmented_image.size
        front_cloud = create_point_cloud(segmented_image, depth_map, width, height)
        back_image, back_depth = flip_image_and_depth(segmented_image, depth_map)
        back_cloud = create_point_cloud(back_image, refine_depth_map(back_depth), width, height)

        combined_cloud = align_and_combine_point_clouds(front_cloud, back_cloud)

        # Mesh generation
        mesh = create_mesh(combined_cloud)

        output_path = os.path.join(settings.STATICFILES_DIRS[0], 'models', 'model_mesh.ply')
        save_mesh(mesh, output_path)

        return render(request, '3d_model.html', {'success_message': '3D model generated successfully!', 
                                                'model_url': os.path.join(settings.STATIC_URL, 'models', 'model_mesh.ply')})

    except Exception as e:
        print(f"Error occurred: {e}")
        return render(request, '3d_model.html', {'error_message': str(e)})