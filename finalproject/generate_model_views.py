import open3d as o3d
import numpy as np
import os
from django.conf import settings
from django.shortcuts import render
from PIL import Image
import torch
from transformers import GLPNImageProcessor, GLPNForDepthEstimation
import cv2


def load_image(image_path):
    try:
        return Image.open(image_path).convert('RGB')
    except Exception as e:
        raise ValueError(f"Failed to load image. Ensure it's a valid image file. Error: {e}")

def segment_image(input_image):
    try:
        image = np.array(input_image)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        mask = np.zeros(image_bgr.shape[:2], dtype=np.uint8)
        height, width = image_bgr.shape[:2]
        rect = (int(width * 0.1), int(height * 0.1), int(width * 0.8), int(height * 0.8))

        bg_model = np.zeros((1, 65), np.float64)  
        fg_model = np.zeros((1, 65), np.float64)  
        cv2.grabCut(image_bgr, mask, rect, bg_model, fg_model, iterCount=5, mode=cv2.GC_INIT_WITH_RECT)

        mask = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

        segmented_image = image * mask[..., None]

        return Image.fromarray(segmented_image), mask
    
    except Exception as e:
        raise RuntimeError(f"Segmentation with OpenCV failed: {e}")

def estimate_depth(input_image, processor, model):
    try:
        inputs = processor(images=input_image, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        return outputs.predicted_depth.squeeze().cpu().numpy()
    except Exception as e:
        raise RuntimeError(f"Depth estimation failed: {e}")


def refine_depth_map(depth_map):
    try:
        depth_map_normalized = (depth_map / np.max(depth_map) * 255).astype('uint8')
        smoothed = cv2.bilateralFilter(depth_map_normalized, d=9, sigmaColor=75, sigmaSpace=75)
        return smoothed / 255.0 * np.max(depth_map)
    except Exception as e:
        raise RuntimeError(f"Depth map refinement failed: {e}")


def create_point_cloud(input_image, depth_map, width, height, object_mask):
    try:
        depth_image = (depth_map * 255 / np.max(depth_map)).astype('uint8')
        input_image_array = np.array(input_image)

        if input_image_array.shape[:2] != depth_image.shape[:2]:
            raise ValueError(f"Image size {input_image.shape[:2]} and depth map size {depth_image.shape[:2]} mismatch.")

        depth_image *= object_mask
        input_image_array *= object_mask[..., None]

        depth_o3d = o3d.geometry.Image(depth_image)
        image_o3d = o3d.geometry.Image(input_image_array)
        rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
            image_o3d, depth_o3d, convert_rgb_to_intensity=False
        )

        camera_intrinsic = o3d.camera.PinholeCameraIntrinsic()
        camera_intrinsic.set_intrinsics(width, height, 500, 500, width / 2, height / 2)

        point_cloud = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, camera_intrinsic)

        return point_cloud
    
    except Exception as e:
        raise RuntimeError(f"Point cloud creation failed: {e}")
    
def create_mesh_from_point_cloud(point_cloud):
    try:
        # Check if the point cloud has points
        if len(point_cloud.points) == 0:
            raise ValueError("Point cloud is empty. Cannot create mesh.")

        # Estimate normals if not already done
        if not point_cloud.has_normals():
            point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

        # Perform Poisson surface reconstruction
        print("Performing Poisson surface reconstruction...")
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(point_cloud, depth=14)

        # Check if the mesh is valid
        if mesh.is_empty():
            raise RuntimeError("Mesh creation resulted in an empty mesh.")

        # Check the number of vertices and densities
        print(f"Mesh has {len(mesh.vertices)} vertices.")
        print(f"Densities array has {densities.size} elements.")

        # Check if densities is not empty
        if densities.size == 0:
            raise ValueError("Densities array is empty. Cannot remove low-density vertices.")
        if len(densities) != len(mesh.vertices):
            raise ValueError(f"Length of densities ({len(densities)}) does not match number of vertices in the mesh ({len(mesh.vertices)}).")

        # Inspect densities
        print("Densities sample:", densities[:10])  # Print the first 10 densities

        # Check for NaN or Inf values
        if np.any(np.isnan(densities)) or np.any(np.isinf(densities)):
            raise ValueError("Densities array contains NaN or Inf values.")

        # Remove vertices with low density
        print("Removing low-density vertices...")
        vertices_to_remove = densities < np.quantile(densities, 0.1)  
        mesh.remove_vertices_by_mask(vertices_to_remove)

        # Alternative smoothing
        print("Smoothing the mesh...")
        mesh = mesh.filter_smooth_simple(number_of_iterations=3)

        # Optionally, remove unreferenced vertices
        mesh.remove_unreferenced_vertices()

        # Refine the mesh with additional smoothing 
        mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=50000)

        # Compute vertex normals
        mesh.compute_vertex_normals()

        print("Mesh created successfully with {} vertices.".format(len(mesh.vertices)))
        return mesh
    
    except Exception as e:
        raise RuntimeError(f"Mesh creation from point cloud failed: {e}")

def save_mesh(mesh, output_path):
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        o3d.io.write_triangle_mesh(output_path, mesh)  
    except Exception as e:
        raise RuntimeError(f"Saving mesh failed: {e}")

def generate_model(request):
    try:
        image_path = request.GET.get('image_path')
        if not image_path:
            return render(request, '3d_model.html', {'error_message': 'Image path is missing in the request.'})

        absolute_image_path = os.path.join(settings.BASE_DIR, image_path.lstrip('/'))

        if not os.path.isfile(absolute_image_path):
            return render(request, '3d_model.html', {'error_message': f"File not found: {absolute_image_path}"})

        input_image = load_image(absolute_image_path)

        # Segmentation with OpenCV GrabCut
        print("Segmenting image...")
        segmented_image, object_mask = segment_image(input_image)

        # Depth estimation step
        processor = GLPNImageProcessor.from_pretrained("vinvino02/glpn-nyu")
        model = GLPNForDepthEstimation.from_pretrained("vinvino02/glpn-nyu")

        new_height = min(segmented_image.height, 480)
        new_height -= new_height % 32
        new_width = (new_height * segmented_image.width // segmented_image.height) // 32 * 32
        segmented_image = segmented_image.resize((new_width, new_height))
        object_mask = cv2.resize(object_mask.astype('uint8'), (new_width, new_height), interpolation=cv2.INTER_NEAREST)

        predicted_depth = estimate_depth(segmented_image, processor, model)

        depth_map = refine_depth_map(predicted_depth)
        depth_map *= object_mask  # Apply the mask to the depth map

        # Generate point cloud
        width, height = segmented_image.size
        point_cloud = create_point_cloud(segmented_image, depth_map, width, height, object_mask)

        # Generate mesh from point cloud
        mesh = create_mesh_from_point_cloud(point_cloud)

        # Save the mesh
        MODEL_DIR = os.path.join(settings.STATICFILES_DIRS[0], 'models')
        MODEL_FILENAME = os.path.join(MODEL_DIR, 'model_mesh.ply')
        save_mesh(mesh, MODEL_FILENAME)

        model_url = os.path.join(settings.STATIC_URL, 'models', 'model_mesh.ply')

        return render(request, '3d_model.html', {'success_message': '3D model generated successfully!', 'model_url': model_url})

    except Exception as e:
        return render(request, '3d_model.html', {'error_message': str(e)})