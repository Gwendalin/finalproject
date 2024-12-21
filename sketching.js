import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
import { getDatabase, ref, set, get } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-database.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-auth.js";
import { getStorage, ref as storageRef, uploadString } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-storage.js";

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyDyvnnQlWsTlO4Qfdj6EqBbHhcC-LNBLu4",
    authDomain: "final-project-8018a.firebaseapp.com",
    databaseURL: "https://final-project-8018a-default-rtdb.firebaseio.com",
    projectId: "final-project-8018a",
    storageBucket: "final-project-8018a.firebasestorage.app",
    messagingSenderId: "951767625787",
    appId: "1:951767625787:web:ba80c0ad4ac3310e60ac1e"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);
const auth = getAuth(app);
const storage = getStorage(app);

let userUID = null;

document.addEventListener('DOMContentLoaded', () => {

    // Initialize Fabric.js Canvas
    const canvas = new fabric.Canvas('designCanvas', {
        height: window.innerHeight,
        width: window.innerWidth
    });

    let drawingType = ''; 
    let currentShape = null; 
    let lineObject = null;
    let bezierCurves = [];
    let currentColor = '#000000';
    let history = [];
    let controlPointsMap = new Map();
    let isDrawing = false;

    function saveState() {
        const canvasState = JSON.stringify(canvas);
        if (history.length === 0 || history[history.length - 1] !== canvasState) {
            history.push(canvasState);
            console.log("State saved. History length:", history.length);
        }
    }

    // Disable conflicting modes
    function disableOtherModes() {
        canvas.isDrawingMode = false;
        drawingType = '';
        currentShape = null;
        isDrawing = false;
    }

    // Undo Last Action
    document.getElementById('undo').addEventListener('click', () => {
        if (history.length > 0) {
            const lastObject = history.pop(); // Get the last object
            canvas.remove(lastObject); // Remove it from the canvas
            console.log('Undo: Removed object from canvas.');
        } else {
            alert('Nothing to undo!');
            console.log('History is empty. Nothing to undo.');
        }
    });

    // Drag Mode
    document.getElementById('drag-mode').addEventListener('click', () => {
        canvas.isDrawingMode = false;
        canvas.selection = true; // Enable object selection
        canvas.forEachObject((o) => o.selectable = true);
        drawingType = '';
    });
    
    document.getElementById('free-draw').addEventListener('click', () => {
        disableOtherModes();
        
        // Activate drawing mode first to ensure freeDrawingBrush is initialized
        canvas.isDrawingMode = true;
    
        // Ensure freeDrawingBrush exists
        if (!canvas.freeDrawingBrush) {
            canvas.freeDrawingBrush = new fabric.PencilBrush(canvas);
        }
    
        // Set brush properties
        canvas.freeDrawingBrush.color = currentColor;
        canvas.freeDrawingBrush.width = 2;
    });   
    
    canvas.on('object:added', (e) => {
        const object = e.target;
        if (object) {
            history.push(object); // Add the object to the history
            console.log('Object added to history:', object);
        }
    });

    // Line button click event
    document.getElementById('line-mode').addEventListener('click', () => {
        disableOtherModes();
        console.log('Line drawing mode activated');
        drawingType = 'line';
    });

    document.getElementById('curve-mode').addEventListener('click', () => {
        disableOtherModes();
        const activeObject = canvas.getActiveObject();
        if (activeObject && activeObject.type === 'line') {
            console.log('Converting line to curve');
            lineObject = activeObject; // Assign the active line to lineObject
            showControlPoints(lineObject);
        } else {
            alert('Please select a line to convert it into a curve.');
        }
    });

    // Rectangle Mode
    document.getElementById('rectangle-mode').addEventListener('click', () => {
        disableOtherModes();
        drawingType = 'rectangle';
    });

    // Circle Mode
    document.getElementById('circle-mode').addEventListener('click', () => {
        disableOtherModes();
        drawingType = 'circle';
    });

    // Eraser Mode
    document.getElementById('eraser-mode').addEventListener('click', () => {
        disableOtherModes();
        drawingType = 'eraser';
        canvas.isDrawingMode = true;
        canvas.freeDrawingBrush.color = 'white'; // Erase by "painting" white
        canvas.freeDrawingBrush.width = 10;
    });
    
    // Color Picker
    document.getElementById('color-picker-button').addEventListener('click', () => {
        document.getElementById('hidden-color-picker').click();
    });

    document.getElementById('hidden-color-picker').addEventListener('input', (e) => {
        const selectedColor = e.target.value;
        currentColor = selectedColor;
    
        // If the user is actively drawing, set the brush color
        if (canvas.isDrawingMode) {
            canvas.freeDrawingBrush.color = selectedColor;
        }
    
        // If a shape (rectangle, circle, etc.) is selected, update its fill color
        const activeObject = canvas.getActiveObject();
        if (activeObject) {
            if (activeObject.type === 'line' || activeObject.type === 'path') {
                // Update stroke color for lines or paths
                activeObject.set({ stroke: selectedColor });
            } else {
                // Update both stroke and fill color for other shapes
                activeObject.set({
                    stroke: selectedColor,
                    fill: selectedColor, // Apply the same color to the fill
                });
            }
            canvas.renderAll(); // Refresh the canvas to apply changes
        }
    });
    

    // Clear Canvas
    document.getElementById('clear-canvas').addEventListener('click', () => {
        if (confirm('Are you sure you want to clear the canvas?')) {
            canvas.clear();
            saveCanvasToFirebase();
        }
    });

    let startX, startY;

    // Mouse down event: Start drawing or transforming
    canvas.on('mouse:down', (e) => {
        const pointer = canvas.getPointer(e.e);
        console.log('Mouse down at:', pointer);

        const target = canvas.findTarget(e.e);
        if (!target || (target.type !== 'circle' && target.type !== 'path')) {
            console.log('Click detected outside control points or curve, clearing control points.');
            removeControlPointsAndCurve(); // Clear control points
        }

        startX = pointer.x;
        startY = pointer.y;
        isDrawing = true;

        if (drawingType === 'free-draw' && !currentShape) {
            // Start free drawing
            canvas.isDrawingMode = true;
            canvas.freeDrawingBrush.color = currentColor;
            canvas.freeDrawingBrush.width = 2; // Set brush width
        } else if (drawingType === 'eraser' && !currentShape) {
            // Eraser mode: Remove the object under the pointer
            const clickedObject = canvas.findTarget(e.e);
            if (clickedObject) {
                console.log('Object erased:', clickedObject);
    
                // Check if the object is a curve (fabric.Path)
                if (clickedObject.type === 'path') {
                    // Remove associated control points and the curve
                    removeControlPointsAndCurve(clickedObject);
                }
    
                // Remove the object from the canvas
                canvas.remove(clickedObject);
                saveState(); // Save the state after erasing
            }
        } else if (drawingType === 'line' && !currentShape) {
            // Create the line on mouse down
            currentShape = new fabric.Line([startX, startY, startX, startY], {
                stroke: currentColor,
                strokeWidth: 2,
                selectable: true, // Make the line selectable after it is drawn
                hasBorders: false, // Disable active state styling
                hasControls: false, // Disable active state styling
            });
            canvas.add(currentShape);
            console.log('Line created:', currentShape);
        } else if (drawingType === 'rectangle' && !currentShape) {
            currentShape = new fabric.Rect({
                left: startX,
                top: startY,
                width: 0,
                height: 0,
                fill: 'transparent',
                stroke: currentColor,
                strokeWidth: 2,
            });
            canvas.add(currentShape);
        } else if (drawingType === 'circle' && !currentShape) {
            currentShape = new fabric.Circle({
                left: startX,
                top: startY,
                radius: 0,
                fill: 'transparent',
                stroke: currentColor,
                strokeWidth: 2,
            });
            canvas.add(currentShape);
        }
    });

    // Mouse move event: Update line's endpoint
    canvas.on('mouse:move', (e) => {
        if (drawingType === 'free-draw') {
            
        } else if (drawingType === 'line' && currentShape) {
            const pointer = canvas.getPointer(e.e);
            currentShape.set({ x2: pointer.x, y2: pointer.y });
            canvas.renderAll();
            console.log('Line updated to:', pointer);
        } else if (drawingType === 'rectangle' && currentShape) {
            const pointer = canvas.getPointer(e.e);
            currentShape.set({
                width: Math.abs(pointer.x - startX),
                height: Math.abs(pointer.y - startY),
            });
            canvas.renderAll();
        } else if (drawingType === 'circle' && currentShape) {
            const pointer = canvas.getPointer(e.e);
            const radius = Math.sqrt(
                Math.pow(pointer.x - startX, 2) +
                Math.pow(pointer.y - startY, 2)
            );
            currentShape.set({ radius });
            canvas.renderAll();
        } else if (drawingType === 'eraser') {
            const clickedObject = canvas.findTarget(e.e); // Find the object under the pointer
            if (clickedObject) {
                canvas.remove(clickedObject); // Remove the object from the canvas
                console.log('Object erased:', clickedObject);
            }
        }
    });

    // Mouse up event: Finalize line
    canvas.on('mouse:up', () => {
        if (drawingType === 'line' && currentShape) {
            currentShape.set({ selectable: true });
            console.log('Line finalized');
            currentShape = null;
            saveState();
        } else if (drawingType === 'rectangle' && currentShape) {
            currentShape.set({ selectable: true });
            currentShape = null;
            isDrawing = false;
            saveState();
        } else if (drawingType === 'circle' && currentShape) {
            currentShape.set({ selectable: true });
            currentShape = null;
            isDrawing = false;
            saveState();
        } else if (drawingType === 'free-draw') {
            // Stop free drawing
            canvas.isDrawingMode = false; // Disable drawing mode
            drawingType = '';
            saveState();
        } else if (drawingType === 'eraser') {
            saveState();
        }
    });

    // Show 4 Control Points (Start, Control1, Control2, End)
    function showControlPoints(line) {
        
        removeControlPointsAndCurve(); // Clear previous controls and curve

        const { x1, y1, x2, y2 } = line;

        // Create four control points
        const start = createControlPoint(x1, y1, () => updateBezierCurve(line));
        const control1 = createControlPoint(x1 + (x2 - x1) / 3, y1, () => updateBezierCurve(line)); 
        const control2 = createControlPoint(x1 + 2 * (x2 - x1) / 3, y1, () => updateBezierCurve(line)); 
        const end = createControlPoint(x2, y2, () => updateBezierCurve(line));


        controlPointsMap.set(line, [start, control1, control2, end]);
    }

    // Create a draggable control point
    function createControlPoint(x, y, onMoveCallback) {
        const point = new fabric.Circle({
            left: x - 5,
            top: y - 5,
            radius: 5,
            fill: 'black',
            selectable: true,
            hasControls: false,
            hasBorders: false,
        });

        point.on('moving', onMoveCallback);
        canvas.add(point);
        return point;
    }

    // Update Bézier Curve Dynamically
    function updateBezierCurve(line) {

        const controlPoints = controlPointsMap.get(line);

        if (!controlPoints || controlPoints.length !== 4) return;

        const [start, c1, c2, end] = controlPoints;

        // Bézier curve path
        const pathData = `
            M ${start.left + 5} ${start.top + 5}
            C ${c1.left + 5} ${c1.top + 5},
            ${c2.left + 5} ${c2.top + 5},
            ${end.left + 5} ${end.top + 5}
        `;

         // Remove existing curve associated with the line
         const existingCurveIndex = bezierCurves.findIndex(item => item.line === line);
         if (existingCurveIndex !== -1) {
             canvas.remove(bezierCurves[existingCurveIndex].curve); // Remove the old curve
             bezierCurves.splice(existingCurveIndex, 1); // Remove it from the array
         }

        // Create and add the new curve
        const curve = new fabric.Path(pathData, {
            stroke: currentColor,
            strokeWidth: 2,
            fill: 'transparent',
            selectable: false,
            evented: false,
        });

        canvas.remove(line);
        canvas.add(curve);
        bezierCurves.push({ line, curve });
        canvas.renderAll();

        saveState();
    }

    // Remove Control Points and Bézier Curve
    function removeControlPointsAndCurve() {
        controlPointsMap.forEach((points) => {
            points.forEach(point => canvas.remove(point));
        });
        controlPointsMap.clear();
        canvas.renderAll();
    }
    

    // Save Canvas State to Firebase
    document.getElementById('save-canvas').addEventListener('click', () => {
        const canvasState = JSON.stringify(canvas); // Serialize the canvas state
        const refPath = `savedCanvas/${Date.now()}`; // Unique path for each canvas
        set(ref(database, refPath), { canvasState })
            .then(() => alert('Canvas saved successfully!'))
            .catch((err) => alert(`Error saving canvas: ${err}`));
    });
    

    // Save Canvas as Image to Firebase Storage
    document.getElementById('save-image').addEventListener('click', () => {
        const imageData = canvas.toDataURL('image/png'); // Convert canvas to base64 image
        const storagePath = `image/${Date.now()}.png`; // Unique path for the image
        const imageRef = storageRef(storage, storagePath);

        uploadString(imageRef, imageData, 'data_url') // Upload base64 string to Firebase Storage
            .then(() => {
                alert('Image saved to Firebase Storage successfully!');
            })
            .catch((err) => {
                alert(`Error saving image to Firebase Storage: ${err.message}`);
            });
    });

    // Open Saved File
    document.getElementById('open-file').addEventListener('click', () => {
        const dropdown = document.getElementById('file'); // Reference the static dropdown in your HTML
        const refPath = 'savedCanvas'; // Path in Firebase Database
    
        // Clear existing options except the default one
        dropdown.innerHTML = '<option value="" disabled selected>Select a canvas</option>';
        dropdown.style.display = 'block';
    
        get(ref(database, refPath))
            .then((snapshot) => {
                if (snapshot.exists()) {
                    const canvases = snapshot.val(); // Get saved canvases
                    console.log('Saved canvases:', canvases);
    
                    // Populate dropdown with saved canvas keys
                    Object.keys(canvases).forEach((key) => {
                        const option = document.createElement('option');
                        option.value = key; // Use the canvas key as the value
                        option.textContent = key; // Display the key or name
                        dropdown.appendChild(option);
                    });
                } else {
                    console.log('No saved canvases found.');
                    alert('No saved canvases found.');
                }
            })
            .catch((err) => {
                console.error('Error fetching saved canvases:', err);
                alert(`Error loading canvas list: ${err.message}`);
            });
    });
    

    document.getElementById('file').addEventListener('change', (e) => {
        const selectedCanvasKey = e.target.value; // Get selected canvas key
        if (!selectedCanvasKey) {
            alert('Please select a canvas to load.');
            return;
        }
    
        const refPath = `savedCanvas/${selectedCanvasKey}`;
        console.log(`Fetching canvas state from path: ${refPath}`);
    
        get(ref(database, refPath))
            .then((snapshot) => {
                if (snapshot.exists()) {
                    console.log('Snapshot data:', snapshot.val());
                    const canvasState = snapshot.val().canvasState; // Get saved state
                    if (canvasState && typeof canvasState === 'string' && canvasState.startsWith('{')) {
                        canvas.loadFromJSON(canvasState, () => {
                            console.log('Canvas loaded successfully.');
                            canvas.renderAll(); // Render the loaded canvas
                        });
                    } else {
                        console.error('Canvas state is missing or invalid for the selected key.');
                        alert('No valid canvas state found for the selected key.');
                    }
                } else {
                    console.error('No canvas found for the selected key.');
                    alert('No canvas found for the selected key.');
                }
            })
            .catch((err) => {
                console.error('Error loading canvas:', err);
                alert(`Error loading canvas: ${err.message}`);
            });
    });
    
    
    

    function showAlert(message, type) {
        // Create an alert element
        const alertBox = document.createElement('div');
        alertBox.className = `alert alert-${type}`; // Assuming you have CSS classes for alerts
        alertBox.innerText = message;

        // Append to body or a specific container
        document.body.appendChild(alertBox);

        // Remove alert after a few seconds
        setTimeout(() => {
            alertBox.remove();
        }, 3000);
    }

});
