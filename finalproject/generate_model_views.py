import open3d as o3d
import numpy as np
import os
from django.conf import settings
from django.shortcuts import render
from PIL import Image
import torch
from transformers import GLPNImageProcessor, GLPNForDepthEstimation
import cv2
import pyvista as pv


def load_image(image_path):
    try:
        return Image.open(image_path).convert('RGB')
    except Exception as e:
        raise ValueError(f"Failed to load image. Ensure it's a valid image file. Error: {e}")

def segment_image(input_image, newmask_path=None):
    try:
        image = np.array(input_image)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        mask = np.zeros(image_bgr.shape[:2], dtype=np.uint8)
        height, width = image_bgr.shape[:2]
        rect = (int(width * 0.05), int(height * 0.05), int(width * 0.9), int(height * 0.9))

        bg_model = np.zeros((1, 65), np.float64)  
        fg_model = np.zeros((1, 65), np.float64) 

        #newmask = cv2.imread(newmask_path, cv2.IMREAD_GRAYSCALE)
        #assert newmask is not None, "file could not be read"

        #mask[newmask == 0] = 0
        #mask[newmask == 255] = 1

        #mask, bg_model, fg_model = cv2.grabCut(image_bgr, mask, None, bg_model, fg_model, 5, cv2.GC_INIT_WITH_MASK)
        
        cv2.grabCut(image_bgr, mask, rect, bg_model, fg_model, iterCount=10, mode=cv2.GC_INIT_WITH_RECT)

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
        smoothed = cv2.bilateralFilter(depth_map_normalized, d=7, sigmaColor=50, sigmaSpace=50)
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

        print(f"Original point cloud has {len(point_cloud.points)} points.")

        # Debug point cloud range
        points = np.asarray(point_cloud.points)
        print("X range:", points[:, 0].min(), "to", points[:, 0].max())
        print("Y range:", points[:, 1].min(), "to", points[:, 1].max())
        print("Z range:", points[:, 2].min(), "to", points[:, 2].max())

        # Reduce the point cloud using voxel downsampling
        voxel_size = 0.001 * (np.ptp(np.asarray(point_cloud.points), axis=0).max())
        print(f"Using voxel size: {voxel_size:.6f}")
        point_cloud = point_cloud.voxel_down_sample(voxel_size=voxel_size)

        print(f"Reduced point cloud has {len(point_cloud.points)} points.")

        return point_cloud
    
    except Exception as e:
        raise RuntimeError(f"Point cloud creation failed: {e}")
    
def create_mesh(point_cloud):
    try:
        # Check if the point cloud has points
        if len(point_cloud.points) == 0:
            raise ValueError("Point cloud is empty. Cannot create mesh.")

        # Clean and prepare point cloud
        cl, ind = point_cloud.remove_statistical_outlier(nb_neighbors=30, std_ratio=1.5)
        clean_point_cloud = point_cloud.select_by_index(ind)

        # Estimate normals
        print("Estimating normals for the point cloud...")
        if len(clean_point_cloud.points) == 0:
            raise RuntimeError("Point cloud is empty after cleaning.")
        
        clean_point_cloud.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.05, max_nn=50)
            )
        clean_point_cloud.orient_normals_consistent_tangent_plane(k=50)
        print(f"Mesh has {point_cloud.has_normals()} normals.")

        # Check normals
        if not clean_point_cloud.has_normals():
             raise RuntimeError("Failed to estimate normals for the point cloud.")

        # Debug: Print original bounding box
        bbox = clean_point_cloud.get_axis_aligned_bounding_box()
        print(f"Original Bounding Box: {bbox}")

        # Scale up the point cloud
        scale_factor = 1000
        clean_point_cloud.scale(scale_factor, center= clean_point_cloud.get_center())
        print(f"Scaled Bounding Box: {clean_point_cloud.get_axis_aligned_bounding_box()}")

        # Perform Poisson surface reconstruction
        print("Performing Poisson surface reconstruction...")
#       radii = [0.004, 0.008, 0.02, 0.04, 0.08]
#       print(f"Using Radii for Ball Pivoting: {radii}")

#       mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(clean_point_cloud, o3d.utility.DoubleVector(radii))

        #o3d.visualization.draw_geometries([point_cloud], point_show_normal=False)
        #radii = [0.005, 0.01, 0.02, 0.04]
        #print(f"Using Radii for Ball Pivoting: {radii}")
        #rec_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(clean_point_cloud, o3d.utility.DoubleVector(radii))
        #o3d.visualization.draw_geometries([point_cloud, rec_mesh])

        with o3d.utility.VerbosityContextManager(o3d.utility.VerbosityLevel.Debug) as cm:
#           mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(clean_point_cloud, o3d.utility.DoubleVector(radii))
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(clean_point_cloud, depth=14)
            print(f"Generated mesh has {len(mesh.vertices)} vertices and {len(mesh.triangles)} triangles.")
#       o3d.visualization.draw_geometries([point_cloud, mesh])

        # Validate the mesh
        if mesh.is_empty():
             raise RuntimeError("Mesh is empty after removing low-density vertices.")
        
        # Remove low-density vertices
        print("Removing low-density vertices...")
        # Ensure densities and vertices are aligned
        densities = np.asarray(densities)

        # Check if densities exist and match vertex count
        if densities.size != len(mesh.vertices):
            raise RuntimeError("Mismatch between mesh vertices and densities.")

        # Threshold to remove low-density vertices
        density_threshold = np.quantile(densities, 0.05)
        vertices_to_remove = densities < density_threshold

        print(f"Removing vertices below density threshold: {density_threshold}")
        mesh.remove_vertices_by_mask(vertices_to_remove)
        mesh.remove_unreferenced_vertices()

        
        # Smoothing the mesh
        print("Smoothing the mesh...")
        mesh = mesh.filter_smooth_laplacian(number_of_iterations=5)
        # Remove unreferenced vertices
        #mesh.remove_unreferenced_vertices()
        # Compute vertex normals
        mesh.compute_vertex_normals()
        print("compute_vertex_normals the mesh...")

        print("Mesh generation completed successfully.")
        return mesh

    except Exception as e:
        raise RuntimeError(f"Mesh creation from point cloud failed: {e}")
    

def save_mesh(mesh, output_path):
    try:
        print("save_mesh")
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

        new_height = min(segmented_image.height, 720)  # Higher resolution
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
        mesh = create_mesh(point_cloud)

        # Render the mesh using Open3D Visualizer
        print("Rendering mesh in Open3D visualizer...")
        o3d.visualization.draw_geometries([mesh])  # Open3D visualization

        # Save the mesh
        MODEL_DIR = os.path.join(settings.STATICFILES_DIRS[0], 'models')
        MODEL_FILENAME = os.path.join(MODEL_DIR, 'model_mesh.ply')
        print("Saving mesh to:", MODEL_FILENAME)
        print("Vertices count:", len(mesh.vertices))
        print("Triangles count:", len(mesh.triangles))
        save_mesh(mesh, MODEL_FILENAME)

        print("Saved successfully")
        model_url = os.path.join(settings.STATIC_URL, 'models', 'model_mesh.ply')

        return render(request, '3d_model.html', {'success_message': '3D model generated successfully!', 'model_url': model_url})

    except Exception as e:
        return render(request, '3d_model.html', {'error_message': str(e)})