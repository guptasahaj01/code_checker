/**
 * app.js - Main JavaScript for the Plagiarism Detection System
 * Handles file uploads and communicating with the backend API
 */

document.addEventListener('DOMContentLoaded', () => {
    // Configuration
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
    const ALLOWED_TYPES = ['application/pdf'];
    
    // DOM Elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const fileListContainer = document.getElementById('fileListContainer');
    const fileList = document.getElementById('fileList');
    const fileCount = document.getElementById('fileCount');
    const clearAllButton = document.getElementById('clearAllButton');
    const processButton = document.getElementById('processButton');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const processingStatus = document.getElementById('processingStatus');
    
    // State
    let selectedFiles = [];
    
    // Initialize
    function init() {
        setupEventListeners();
        checkBackendConnection();
    }
    
    // Check if backend is available
    function checkBackendConnection() {
        fetch('http://127.0.0.1:5010/api/health')
            .then(response => response.json())
            .then(data => {
                console.log('Backend connection successful:', data);
                if (data.backend_mode === 'fallback') {
                    console.log('Backend running in fallback mode');
                }
            })
            .catch(error => {
                console.error('Backend connection failed:', error);
            });
    }
    
    // Setup Event Listeners
    function setupEventListeners() {
        // File drop area
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        // File input
        fileInput.addEventListener('change', handleFileInputChange);
        
        // Buttons
        clearAllButton.addEventListener('click', clearAllFiles);
        processButton.addEventListener('click', processFiles);
    }
    
    // Helper functions
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        uploadArea.classList.add('highlight');
    }
    
    function unhighlight() {
        uploadArea.classList.remove('highlight');
    }
    
    // File handling
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    function handleFileInputChange() {
        const files = fileInput.files;
        handleFiles(files);
    }
    
    function handleFiles(files) {
        // Convert to array and filter by file type
        const filesArray = Array.from(files);
        const validFiles = filesArray.filter(file => {
            if (!ALLOWED_TYPES.includes(file.type)) {
                showError(`'${file.name}' is not a PDF file.`);
                return false;
            }
            
            if (file.size > MAX_FILE_SIZE) {
                showError(`'${file.name}' exceeds the maximum file size of 50MB.`);
                return false;
            }
            
            return true;
        });
        
        // Add valid files to selected files array (avoiding duplicates)
        validFiles.forEach(file => {
            if (!selectedFiles.some(f => f.name === file.name)) {
                selectedFiles.push(file);
            }
        });
        
        updateFileList();
    }
    
    function updateFileList() {
        // Update the file count display
        fileCount.textContent = selectedFiles.length;
        
        // Show/hide file list container
        if (selectedFiles.length > 0) {
            fileListContainer.style.display = 'block';
        } else {
            fileListContainer.style.display = 'none';
        }
        
        // Update button states
        clearAllButton.disabled = selectedFiles.length === 0;
        processButton.disabled = selectedFiles.length === 0;
        
        // Render file list
        fileList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const li = document.createElement('li');
            li.className = 'file-item';
            li.innerHTML = `
                <span class="file-name">${file.name}</span>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <button class="file-remove" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            fileList.appendChild(li);
            
            // Add event listener to remove button
            const removeBtn = li.querySelector('.file-remove');
            removeBtn.addEventListener('click', () => removeFile(index));
        });
    }
    
    function removeFile(index) {
        selectedFiles.splice(index, 1);
        updateFileList();
    }
    
    function clearAllFiles() {
        selectedFiles = [];
        fileInput.value = '';
        updateFileList();
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    function showError(message) {
        // Simple alert for now, could be replaced with a nicer UI
        alert(message);
    }
    
    // Process files
    function processFiles() {
        if (selectedFiles.length === 0) {
            showError('Please select at least one file to process.');
            return;
        }
        
        // Get selected difficulty
        const difficultyInputs = document.querySelectorAll('input[name="difficulty"]');
        let difficulty = 'medium';
        for (const input of difficultyInputs) {
            if (input.checked) {
                difficulty = input.value;
                break;
            }
        }
        
        // Show loading overlay
        loadingOverlay.style.display = 'flex';
        processingStatus.textContent = 'Uploading files...';
        
        // Create form data
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('difficulty', difficulty);
        
        // Upload files and process
        fetch('http://127.0.0.1:5010/api/plagiarism/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Processing submitted successfully:', data);
            processingStatus.textContent = 'Processing complete! Redirecting to results...';
            
            // Store session ID in localStorage
            if (data.session_id) {
                localStorage.setItem('plagiarism_session_id', data.session_id);
            }
            
            // Redirect to results page after a short delay
            setTimeout(() => {
                window.location.href = `results.html?session=${data.session_id}`;
            }, 1000);
        })
        .catch(error => {
            console.error('Error processing files:', error);
            processingStatus.textContent = `Error: ${error.message}`;
            
            // Show error for a few seconds, then hide overlay
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 3000);
        });
    }
    
    // Start the application
    init();
}); 