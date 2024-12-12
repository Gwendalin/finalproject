
// Initialize Fabric.js Canvas
const canvas = new fabric.Canvas('designCanvas', {
    height: window.innerHeight,
    width: window.innerWidth,
});

// State variables
let drawingType = '';
let currentShape = null;
let controlPoints = [];
let undoStack = [];
let fillColor = 'transparent';
let isErasing = false;

// Tool activation
document.getElementById('line-mode').addEventListener('click', () => {
    resetTools();
    drawingType = 'line';
});

document.getElementById('eraser-mode').addEventListener('click', () => {
    resetTools();
    isErasing = true;
});

document.getElementById('clear-canvas').addEventListener('click', () => {
    if (confirm('Are you sure you want to clear the canvas?')) {
        canvas.clear();
        undoStack = [];
    }
});

document.getElementById('undo').addEventListener('click', () => {
    if (undoStack.length > 0) {
        const lastObject = undoStack.pop();
        canvas.remove(lastObject);
    }
});

// Function to create draggable control points
function createControlPoint(x, y, onMove) {
    const point = new fabric.Circle({
        left: x,
        top: y,
        radius: 5,
        fill: 'blue',
        stroke: 'black',
        strokeWidth: 1,
        hasControls: false,
        hasBorders: false,
        selectable: true,
        originX: 'center',
        originY: 'center',
    });

    point.on('moving', onMove);
    canvas.add(point);
    return point;
}

// Update line into a curve using control points
function updateLineToCurve(line, start, control, end) {
    const pathData = `
        M ${start.left} ${start.top}
        Q ${control.left} ${control.top}
            ${end.left} ${end.top}`;
    const curve = new fabric.Path(pathData, {
        stroke: 'black',
        strokeWidth: 2,
        fill: 'transparent',
        selectable: false,
    });

    canvas.remove(line);
    canvas.add(curve);
    undoStack.push(curve);

    return curve;
}

// Mouse down event
canvas.on('mouse:down', (e) => {
    const pointer = canvas.getPointer(e.e);

    if (isErasing) {
        eraseAtPointer(pointer);
    } else if (drawingType === 'line') {
        if (!currentShape) {
            // Start a new line
            currentShape = new fabric.Line([pointer.x, pointer.y, pointer.x, pointer.y], {
                stroke: 'black',
                strokeWidth: 2,
                selectable: true,
            });
            canvas.add(currentShape);
            undoStack.push(currentShape);
        } else if (controlPoints.length === 0) {
            // Add control points to transform the line into a curve
            const [x1, y1, x2, y2] = currentShape.calcLinePoints();
            const startPoint = createControlPoint(currentShape.left + x1, currentShape.top + y1, () => updateCurve());
            const endPoint = createControlPoint(currentShape.left + x2, currentShape.top + y2, () => updateCurve());
            const controlPoint = createControlPoint(
                (startPoint.left + endPoint.left) / 2,
                (startPoint.top + endPoint.top) / 2,
                () => updateCurve()
            );

            controlPoints = [startPoint, controlPoint, endPoint];
            updateCurve();
        }
    }
});

// Update the line into a curve dynamically
function updateCurve() {
    if (controlPoints.length === 3) {
        const [start, control, end] = controlPoints;
        currentShape = updateLineToCurve(currentShape, start, control, end);
    }
}

// Mouse move event
canvas.on('mouse:move', (e) => {
    const pointer = canvas.getPointer(e.e);

    if (isErasing) {
        eraseAtPointer(pointer);
    } else if (drawingType === 'line' && currentShape) {
        currentShape.set({ x2: pointer.x, y2: pointer.y });
        canvas.renderAll();
    }
});

// Mouse up event
canvas.on('mouse:up', () => {
    if (drawingType === 'line' && currentShape && controlPoints.length === 0) {
        // Lock the initial line after drawing
        currentShape.set({ selectable: false });
        canvas.renderAll();
    }
});

// Reset tools and states
function resetTools() {
    drawingType = '';
    currentShape = null;
    controlPoints = [];
    isErasing = false;
}

// Erase objects at the pointer position
function eraseAtPointer(pointer) {
    const eraserRadius = 20; // Set a fixed eraser size for now

    const eraserCircle = new fabric.Circle({
        left: pointer.x,
        top: pointer.y,
        radius: eraserRadius,
        originX: 'center',
        originY: 'center',
    });

    // Filter objects intersecting with the eraser circle
    const objectsToErase = canvas.getObjects().filter((obj) =>
        obj.intersectsWithObject(eraserCircle)
    );

    objectsToErase.forEach((obj) => {
        canvas.remove(obj); // Remove objects from canvas
        const index = undoStack.indexOf(obj);
        if (index > -1) {
            undoStack.splice(index, 1);
        }
    });

    canvas.renderAll();
}

