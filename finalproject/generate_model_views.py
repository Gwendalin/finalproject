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


def create_point_cloud(input_image, depth_map, width, height):
    try:
        depth_image = (depth_map * 255 / np.max(depth_map)).astype('uint8')
        input_image_array = np.array(input_image)

        if input_image_array.shape[:2] != depth_image.shape[:2]:
            raise ValueError(f"Image size {input_image.shape[:2]} and depth map size {depth_image.shape[:2]} mismatch.")

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
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(point_cloud, depth=12)

        # Check if the mesh is valid
        if mesh.is_empty():
            raise RuntimeError("Mesh creation resulted in an empty mesh.")

        # Remove vertices with low density
        print("Removing low-density vertices...")
        vertices_to_remove = densities < np.quantile(densities, 0.1)  
        mesh.remove_vertices_by_mask(vertices_to_remove)

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

        print("Received image path:", image_path)

        absolute_image_path = os.path.join(settings.BASE_DIR, image_path.lstrip('/'))
        print("Absolute image path:", absolute_image_path)

        # Ensure the file exists
        if not os.path.isfile(absolute_image_path):
            return render(request, '3d_model.html', {'error_message': f"File not found: {absolute_image_path}"})

        # Load and resize the image
        print("Loading image...")
        input_image = load_image(absolute_image_path)
        processor = GLPNImageProcessor.from_pretrained("vinvino02/glpn-nyu")
        model = GLPNForDepthEstimation.from_pretrained("vinvino02/glpn-nyu")

        # Ensure dimensions are multiples of 32
        new_height = min(input_image.height, 480)
        new_height -= new_height % 32
        new_width = (new_height * input_image.width // input_image.height) // 32 * 32
        input_image = input_image.resize((new_width, new_height))

        # Estimate and refine depth map
        print("Estimating depth...")
        predicted_depth = estimate_depth(input_image, processor, model)
        print("Depth estimation completed.")

        print("Refining depth map...")
        depth_map = refine_depth_map(predicted_depth)
        print(f"Depth map shape: {depth_map.shape}")

        # Process the depth map and image
        pad = 16
        depth_map = np.clip(depth_map * 1000.0, 0, 5000)[pad:-pad, pad:-pad]
        input_image = input_image.crop((pad, pad, input_image.width - pad, input_image.height - pad))
        width, height = input_image.size

        # Generate point cloud and clean it
        print("Creating point cloud...")
        point_cloud = create_point_cloud(input_image, depth_map, width, height)
        print(f"Point cloud created with {len(point_cloud.points)} points.")

        # Remove outliers and densify the point cloud
        cl, ind = point_cloud.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        point_cloud = point_cloud.select_by_index(ind)

         # Create mesh from point cloud
        print("Creating mesh from point cloud...")
        mesh = create_mesh_from_point_cloud(point_cloud)
        print("Mesh created successfully.")

        # Save point cloud as mesh (optional)
        MODEL_DIR = os.path.join(settings.STATICFILES_DIRS[0], 'models')
        MODEL_FILENAME = os.path.join(MODEL_DIR, 'model_mesh.ply')
        print(f"Saving point cloud to {MODEL_FILENAME}...")
        save_mesh(mesh, MODEL_FILENAME)
        print("Mesh saved successfully.")

        # Generate the model URL
        model_url = os.path.join(settings.STATIC_URL, 'models', 'model_point_cloud.ply')

        return render(request, '3d_model.html', {'success_message': '3D model generated successfully!', 'model_url': model_url})

    except Exception as e:
        print("Error during mesh processing:", str(e))
        return render(request, '3d_model.html', {'error_message': str(e)})