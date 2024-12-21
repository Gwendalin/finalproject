// Import Firebase modules
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
import { getDatabase, ref, get, set, remove } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-database.js";

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

let activePicker = null; // Declare a global variable to track the active picker

function openColorPicker(index, event) {
    if (activePicker) {
        activePicker.classList.add("d-none"); // Hide the previously active picker
    }
    const colorPicker = document.getElementById(`color-picker-${index}`);
    activePicker = colorPicker;

    // Position the color picker next to the clicked color box
    const rect = event.target.getBoundingClientRect();
    colorPicker.style.position = "absolute";
    colorPicker.style.left = `${rect.left}px`;
    colorPicker.style.top = `${rect.bottom}px`;
    colorPicker.classList.remove("d-none");

    colorPicker.click(); // Open the color picker
}

// Function to update the color dynamically
function updateColor(input, index) {
    const newColor = input.value; // Get selected color
    const colorBox = document.getElementById(`color-box-${index}`);
    const hexCodeElement = document.getElementById(`hex-code-${index}`);

    // Update the color box
    if (colorBox) colorBox.style.backgroundColor = newColor;

    // Update hex code if available
    if (hexCodeElement) hexCodeElement.textContent = newColor;
}


// Function to toggle save state
function toggleSaveColor(hexColor, starIcon) {
    const savedRef = ref(database, "savedColors");

    get(savedRef).then(snapshot => {
        const savedColors = snapshot.val() || {};
        const isSaved = Object.values(savedColors).includes(hexColor);

        if (!isSaved) {
           // Save color to Firebase
           const newKey = Date.now();
           set(ref(database, `savedColors/${newKey}`), hexColor).then(() => {
               // Show success message
               showSuccessMessage(`Color ${hexColor} saved successfully!`);
               starIcon.classList.remove("bi-star");
               starIcon.classList.add("bi-star-fill", "text-warning");
           });
        }
    });
}

// Function to show a success message
function showSuccessMessage(message, type = 'success') {
    // Clear any existing alerts
    const alertBox = document.getElementById('alert-box');

    // Create the alert dynamically
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    // Inject the alert into the container
    alertBox.innerHTML = alertHTML;

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        alertBox.innerHTML = '';
    }, 3000);
}

// Expose functions globally
window.openColorPicker = openColorPicker;
window.updateColor = updateColor;
window.toggleSaveColor = toggleSaveColor;
window.showSuccessMessage = showSuccessMessage;
