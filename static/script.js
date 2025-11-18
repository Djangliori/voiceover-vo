// Georgian Voiceover App - Client-side JavaScript

let currentJobId = null;
let statusCheckInterval = null;

// DOM Elements
const urlInput = document.getElementById('youtube-url');
const processBtn = document.getElementById('process-btn');
const statusSection = document.getElementById('status-section');
const resultSection = document.getElementById('result-section');
const errorSection = document.getElementById('error-section');
const progressFill = document.getElementById('progress-fill');
const statusMessage = document.getElementById('status-message');
const statusPercent = document.getElementById('status-percent');
const videoTitle = document.getElementById('video-title');
const errorMessage = document.getElementById('error-message');
const downloadBtn = document.getElementById('download-btn');
const newVideoBtn = document.getElementById('new-video-btn');
const retryBtn = document.getElementById('retry-btn');

// Event Listeners
processBtn.addEventListener('click', processVideo);
newVideoBtn.addEventListener('click', resetForm);
retryBtn.addEventListener('click', resetForm);

urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        processVideo();
    }
});

// Process Video
async function processVideo() {
    const url = urlInput.value.trim();

    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }

    if (!isValidYouTubeUrl(url)) {
        showError('Please enter a valid YouTube URL');
        return;
    }

    // Reset UI
    hideAllSections();
    statusSection.classList.remove('hidden');
    processBtn.disabled = true;

    try {
        // Start processing
        const response = await fetch('/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Processing failed');
        }

        currentJobId = data.job_id;

        // Start polling for status immediately
        startStatusPolling();

    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
        processBtn.disabled = false;
    }
}

// Start polling for status updates
function startStatusPolling() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    // Poll every 500ms for faster progress updates
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${currentJobId}`);
            const data = await response.json();

            if (response.ok) {
                updateStatus(data);

                if (data.complete) {
                    clearInterval(statusCheckInterval);
                    showResult(data);
                }
            } else {
                throw new Error(data.error || 'Status check failed');
            }

        } catch (error) {
            console.error('Status check error:', error);
            clearInterval(statusCheckInterval);
            showError('Lost connection to server');
        }
    }, 500); // Check every 500ms for faster updates
}

// Update status display
function updateStatus(data) {
    const progress = data.progress || 0;
    const status = data.status || 'Processing...';

    progressFill.style.width = `${progress}%`;
    statusMessage.textContent = status;
    statusPercent.textContent = `${progress}%`;
}

// Show result
function showResult(data) {
    hideAllSections();
    resultSection.classList.remove('hidden');
    processBtn.disabled = false;

    videoTitle.textContent = `"${data.title}"`;

    downloadBtn.onclick = () => {
        window.location.href = `/download/${data.output_file}`;
    };
}

// Show error
function showError(message) {
    hideAllSections();
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
    processBtn.disabled = false;

    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
}

// Reset form
function resetForm() {
    urlInput.value = '';
    hideAllSections();
    processBtn.disabled = false;
    currentJobId = null;

    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
}

// Hide all sections
function hideAllSections() {
    statusSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

// Validate YouTube URL
function isValidYouTubeUrl(url) {
    const patterns = [
        /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/,
        /^(https?:\/\/)?(www\.)?youtube\.com\/shorts\/[\w-]+/,
    ];

    return patterns.some(pattern => pattern.test(url));
}

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
});
