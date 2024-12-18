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
    storageBucket: "final-project-8018a.appspot.com",
    messagingSenderId: "951767625787",
    appId: "1:951767625787:web:ba80c0ad4ac3310e60ac1e"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);
const auth = getAuth(app);
const storage = getStorage(app);

let userUID = null;

// Check for the currently authenticated user
onAuthStateChanged(auth, (user) => {
    if (user) {
        userUID = user.uid; // Get the authenticated user's UID dynamically
        console.log("Logged-in user UID:", userUID);
        
        // Set the database reference dynamically
        const dbRef = ref(database, `savedDesigns/${userUID}`);

        // Call loadCanvasFromFirebase after userUID is set
        loadCanvasFromFirebase(dbRef);
    } else {
        console.log("No user is logged in.");
        showAlert("Please log in to save or load your designs.", "warning");
    }
});

// Initialize Fabric.js Canvas
const canvas = new fabric.Canvas('designCanvas', {
    height: window.innerHeight - 100,
    width: window.innerWidth - 20,
});

let drawingType = ''; 
let currentShape = null; 
let controlPoints = []; 
let lineObject = null;
let bezierCurve = null;
let currentColor = '#000000';

// Disable conflicting modes
function disableOtherModes() {
    canvas.isDrawingMode = false;
    drawingType = '';
}

// Undo Last Action
document.getElementById('undo').addEventListener('click', () => {
    if (history.length > 0) {
        canvas.loadFromJSON(history.pop(), () => {
            canvas.renderAll();
        });
    }
});

// Drag Mode
document.getElementById('drag-mode').addEventListener('click', () => {
    canvas.isDrawingMode = false;
    canvas.selection = true; // Enable object selection
    canvas.forEachObject((o) => o.selectable = true);
    drawingType = '';
});

// Free Drawing Mode
document.getElementById('free-draw').addEventListener('click', () => {
    disableOtherModes();
    canvas.isDrawingMode = true;
    canvas.freeDrawingBrush.color = currentColor;
    canvas.freeDrawingBrush.width = 2;
});


// Line button click event
document.getElementById('line-mode').addEventListener('click', () => {
    console.log('Line drawing mode activated');
    drawingType = 'line';
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
    canvas.isDrawingMode = true;
    canvas.freeDrawingBrush.color = 'white'; // Erase by "painting" white
});

document.getElementById('eraser-size').addEventListener('input', (e) => {
    canvas.freeDrawingBrush.width = e.target.value;
});

// Color Picker
document.getElementById('color-picker-button').addEventListener('click', () => {
    document.getElementById('color-picker').click();
});

document.getElementById('color-picker').addEventListener('input', (e) => {
    currentColor = e.target.value;
    canvas.freeDrawingBrush.color = currentColor;

    // Change color of selected object
    const activeObject = canvas.getActiveObject();
    if (activeObject) {
        if (activeObject.type === 'line') {
            activeObject.set({ stroke: currentColor });
        } else {
            activeObject.set({ fill: currentColor });
        }
        canvas.renderAll();
    }
});

// Clear Canvas
document.getElementById('clear-canvas').addEventListener('click', () => {
    if (confirm('Are you sure you want to clear the canvas?')) {
        canvas.clear();
        saveCanvasToFirebase();
    }
});

// Mouse down event: Start drawing or transforming
canvas.on('mouse:down', (e) => {
    const pointer = canvas.getPointer(e.e);
    console.log('Mouse down at:', pointer);

    if (drawingType === 'line' && !currentShape) {
        // Create the line on mouse down
        currentShape = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], {
            stroke: 'black',
            strokeWidth: 2,
            selectable: true, // Make the line selectable after it is drawn
            hasBorders: false, // Disable active state styling
            hasControls: false, // Disable active state styling
        });
        canvas.add(currentShape);
        console.log('Line created:', currentShape);
    } else if (!drawingType && lineObject) {
        // If a shape is clicked, check if it’s the one we want to transform
        const clickedObject = canvas.findTarget(e.e); // Get the clicked object
        console.log('Clicked Object:', clickedObject);

        if (clickedObject) {

            // Check if the clicked object is the line
            if (clickedObject === lineObject) {
                console.log('Line clicked, show control points');
                showControlPoints(lineObject);
            }
        } else {
            console.log('No object clicked.');
            removeControlPointsAndCurve();
        }
    } else if (drawingType === 'rectangle') {
        const rect = new fabric.Rect({
            left: pointer.x,
            top: pointer.y,
            width: 0,
            height: 0,
            fill: 'transparent',
            stroke: currentColor,
            strokeWidth: 2,
        });
        canvas.add(rect);
        canvas.setActiveObject(rect);

        canvas.on('mouse:move', function moveHandler(e) {
            const pointer = canvas.getPointer(e.e);
            rect.set({
                width: Math.abs(pointer.x - rect.left),
                height: Math.abs(pointer.y - rect.top),
            });
            canvas.renderAll();
        });

        canvas.on('mouse:up', function upHandler() {
            canvas.off('mouse:move', moveHandler);
            canvas.off('mouse:up', upHandler);
        });

    } else if (drawingType === 'circle') {
        const circle = new fabric.Circle({
            left: pointer.x,
            top: pointer.y,
            radius: 0,
            fill: 'transparent',
            stroke: currentColor,
            strokeWidth: 2,
        });
        canvas.add(circle);
        canvas.setActiveObject(circle);

        canvas.on('mouse:move', function moveHandler(e) {
            const pointer = canvas.getPointer(e.e);
            const radius = Math.sqrt(
                Math.pow(pointer.x - circle.left, 2) +
                Math.pow(pointer.y - circle.top, 2)
            );
            circle.set({ radius });
            canvas.renderAll();
        });

        canvas.on('mouse:up', function upHandler() {
            canvas.off('mouse:move', moveHandler);
            canvas.off('mouse:up', upHandler);
        });
    }
});

// Mouse move event: Update line's endpoint
canvas.on('mouse:move', (e) => {
    if (drawingType === 'line' && currentShape) {
        const pointer = canvas.getPointer(e.e);
        currentShape.set({ x2: pointer.x, y2: pointer.y });
        canvas.renderAll();
        console.log('Line updated to:', pointer);
    } 
});

// Mouse up event: Finalize line
canvas.on('mouse:up', () => {
    if (drawingType === 'line' && currentShape) {
        currentShape.set({ selectable: true });
        lineObject = currentShape;
        console.log('Line Object Assigned:', lineObject);
        currentShape = null; 
        drawingType = ''; // Reset drawing type
        console.log('Line finalized:', currentShape);
    } 
});

// Show 4 Control Points (Start, Control1, Control2, End)
function showControlPoints(line) {
    removeControlPointsAndCurve(); // Clear previous controls and curve

    const { x1, y1, x2, y2 } = line;

    // Create four control points
    const start = createControlPoint(x1, y1, updateBezierCurve); // Start Point
    const control1 = createControlPoint(x1 + (x2 - x1) / 3, y1, updateBezierCurve); 
    const control2 = createControlPoint(x1 + 2 * (x2 - x1) / 3, y1, updateBezierCurve); 
    const end = createControlPoint(x2, y2, updateBezierCurve);

    controlPoints = [start, control1, control2, end];
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
function updateBezierCurve() {
    if (controlPoints.length !== 4) return;

    const [start, c1, c2, end] = controlPoints;

    // Bézier curve path
    const pathData = `
        M ${start.left + 5} ${start.top + 5}
        C ${c1.left + 5} ${c1.top + 5},
        ${c2.left + 5} ${c2.top + 5},
        ${end.left + 5} ${end.top + 5}
    `;

    // Remove the old Bézier curve
    if (bezierCurve) canvas.remove(bezierCurve);

    // Create and add the new Bézier curve
    bezierCurve = new fabric.Path(pathData, {
        stroke: 'blue',
        strokeWidth: 2,
        fill: 'transparent',
        selectable: false,
        evented: false,
    });

    // Remove the original straight line
    if (lineObject) {
        canvas.remove(lineObject);
        lineObject = null; // Clear the reference
    }

    canvas.add(bezierCurve);
    canvas.renderAll();
}

// Remove Control Points and Bézier Curve
function removeControlPointsAndCurve() {
    controlPoints.forEach(point => canvas.remove(point));
    controlPoints = [];
    canvas.renderAll();
}

// Save Canvas State to Firebase
document.getElementById('save-canvas').addEventListener('click', () => {
    const canvasState = JSON.stringify(canvas);
    const refPath = 'savedCanvas';
    set(ref(database, refPath), { canvasState })
        .then(() => alert('Canvas saved successfully!'))
        .catch((err) => alert(`Error saving canvas: ${err}`));
});

// Save Canvas as Image to Firebase Storage
document.getElementById('save-image').addEventListener('click', () => {
    const imageData = canvas.toDataURL('image/png'); // Convert canvas to base64 image
    const storagePath = `images/${Date.now()}.png`; // Unique path for the image
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
    const refPath = 'savedCanvas';
    get(ref(database, refPath))
        .then((snapshot) => {
            if (snapshot.exists()) {
                const canvasState = snapshot.val().canvasState;
                canvas.loadFromJSON(canvasState, () => canvas.renderAll());
            } else {
                alert('No saved canvas found.');
            }
        })
        .catch((err) => alert(`Error loading canvas: ${err}`));
});
