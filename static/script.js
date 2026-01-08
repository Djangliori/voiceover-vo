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
const videoPreview = document.getElementById('video-preview');
const youtubeEmbed = document.getElementById('youtube-embed');

// Event Listeners
processBtn.addEventListener('click', processVideo);
newVideoBtn.addEventListener('click', resetForm);
retryBtn.addEventListener('click', resetForm);

urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        processVideo();
    }
});

// Update video preview when URL changes
urlInput.addEventListener('input', () => {
    updateVideoPreview();
});

urlInput.addEventListener('blur', () => {
    updateVideoPreview();
});

// Update video preview
function updateVideoPreview() {
    const url = urlInput.value.trim();

    if (!url) {
        videoPreview.classList.add('hidden');
        return;
    }

    // Extract video ID from URL
    const videoId = extractVideoId(url);

    if (videoId) {
        // Show embed
        youtubeEmbed.src = `https://www.youtube.com/embed/${videoId}`;
        videoPreview.classList.remove('hidden');
    } else {
        videoPreview.classList.add('hidden');
    }
}

// Extract video ID from YouTube URL
function extractVideoId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/,
        /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }

    return null;
}

// Check URL parameters for auto-filling (but not auto-starting)
window.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const videoId = params.get('v');

    if (videoId) {
        // Auto-fill input with YouTube URL
        const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
        urlInput.value = youtubeUrl;

        // Show video preview immediately
        updateVideoPreview();

        console.log('Video loaded:', videoId, '- Ready to translate');

        // Don't auto-start - let user click the button when ready
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
            // Handle login required
            if (data.login_required) {
                window.location.href = '/login';
                return;
            }

            // Handle quota exceeded
            if (data.quota_exceeded) {
                showError(`You have used all your minutes for this month. Current plan: ${data.tier?.display_name || 'Free'}. Please upgrade to continue.`);
                processBtn.disabled = false;
                return;
            }

            throw new Error(data.error || 'Processing failed');
        }

        // If already processed, redirect to player immediately
        if (data.already_processed) {
            window.location.href = `/watch?v=${data.video_id}`;
            return;
        }

        currentJobId = data.job_id || data.video_id;

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
    // Auto-redirect to watch page when processing completes
    // This provides YouTube-like experience on voyoutube.com/watch?v=VIDEO_ID
    if (data.video_id) {
        console.log('Processing complete! Redirecting to watch page...');
        window.location.href = `/watch?v=${data.video_id}`;
        return;
    }

    // Fallback: show result section if no video_id
    hideAllSections();
    resultSection.classList.remove('hidden');
    processBtn.disabled = false;

    videoTitle.textContent = data.title ? `"${data.title}"` : 'Video processing complete!';

    // Handle download/view button
    downloadBtn.onclick = () => {
        if (data.r2_url) {
            // If R2 URL available, open in new tab or download
            if (data.r2_url.startsWith('http')) {
                window.open(data.r2_url, '_blank');
            } else {
                window.location.href = data.r2_url;
            }
        } else if (data.output_file) {
            window.location.href = `/download/${data.output_file}`;
        } else {
            // Fallback: reload to watch page
            window.location.href = `/watch?v=${data.video_id}`;
        }
    };

    // Update button text
    downloadBtn.querySelector('.btn-text').textContent = data.r2_url && data.r2_url.startsWith('http') ? 'Watch Video' : 'Download Video';
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
