/**
 * results.js - JavaScript for the Plagiarism Detection Results page
 * Fetches and displays plagiarism detection results from the backend
 */

document.addEventListener('DOMContentLoaded', () => {
    // Configuration
    
    // DOM Elements
    const loadingOverlay = document.getElementById('loadingOverlay');
    const errorOverlay = document.getElementById('errorOverlay');
    const errorMessage = document.getElementById('errorMessage');
    const backButton = document.getElementById('backButton');
    const loadingStatus = document.getElementById('loadingStatus');
    
    // Results containers
    const fileCountSummary = document.getElementById('fileCountSummary');
    const analysisTime = document.getElementById('analysisTime');
    const difficultyLevel = document.getElementById('difficultyLevel');
    const similarityResults = document.getElementById('similarityResults');
    const aiResults = document.getElementById('aiResults');
    const webResults = document.getElementById('webResults');
    
    // State
    let sessionId = null;
    let resultData = null;
    
    // Initialize
    function init() {
        setupTabNavigation();
        getSessionId();
        setupBackButton();
        loadResults();
    }
    
    // Setup tab navigation
    function setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Remove active class from all buttons and contents
                tabButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                // Add active class to clicked button and corresponding content
                button.classList.add('active');
                const tabId = button.getAttribute('data-tab');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }
    
    // Setup back button
    function setupBackButton() {
        backButton.addEventListener('click', () => {
            window.location.href = 'index.html';
        });
    }
    
    // Get session ID from URL or localStorage
    function getSessionId() {
        // Check URL query parameters first
        const urlParams = new URLSearchParams(window.location.search);
        sessionId = urlParams.get('session');
        
        // If not in URL, try localStorage
        if (!sessionId) {
            sessionId = localStorage.getItem('plagiarism_session_id');
        }
        
        if (!sessionId) {
            showError('No session ID found. Please upload files first.');
            return false;
        }
        
        console.log('Using session ID:', sessionId);
        return true;
    }
    
    // Load results from API
    function loadResults() {
        if (!getSessionId()) return;
        
        showLoading(true);
        loadingStatus.textContent = 'Fetching results...';
        
        fetch(`http://127.0.0.1:5010/api/results/${sessionId}`)
            .then(response => {
                if (response.status === 202) {
                    // Still processing
                    return response.json().then(data => {
                        loadingStatus.textContent = data.message || 'Processing in progress...';
                        
                        // Poll again after a delay
                        setTimeout(loadResults, 2000);
                        throw new Error('PROCESSING');
                    });
                }
                
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                
                return response.json();
            })
            .then(data => {
                resultData = data;
                console.log(resultData);
                
                displayResults();
                showLoading(false);
            })
            .catch(error => {
                if (error.message === 'PROCESSING') {
                    // This is a normal processing state, not an error
                    return;
                }
                
                console.error('Error loading results:', error);
                showError(`Failed to load results: ${error.message}`);
            });
    }
    
    // Display results
    function displayResults() {
        if (!resultData) {
            showError('No results data available');
            return;
        }
        
        // Update summary information
        updateSummary();
        
        // Update each results section
        displaySimilarityResults();
        displayAIResults();
        displayWebResults();
    }
    
    // Update summary information
    function updateSummary() {
        const fileCount = resultData.metadata.file_count || 0;
        fileCountSummary.textContent = `${fileCount} File${fileCount !== 1 ? 's' : ''}`;

        
        if (resultData.metadata.timestamp) {
            const date = new Date(resultData.metadata.timestamp);
            analysisTime.textContent = `Analysis: ${date.toLocaleString()}`;
        }
        
        if (resultData.metadata.difficulty) {
            difficultyLevel.textContent = `Difficulty: ${resultData.metadata.difficulty.charAt(0).toUpperCase() + resultData.metadata.difficulty.slice(1)}`;
        }
    }
    
    // Display similarity results
    function displaySimilarityResults() {
        const similarityData = resultData.results.similarity_analysis || [];
        
        if (Object.keys(similarityData).length=== 0) {
            similarityResults.innerHTML = '<div class="no-results">Inadequate number of submissions provided to compare.</div>';
            return;
        }
        
        let html = '';
        
        Object.entries(similarityData).forEach(([groupId, groupData], index) => {
            const similarity = (groupData.average_similarity)*100 || 0;
            const severityClass = getSeverityClass(similarity);
            
            // Extract solution number from groupId (format: solutionX)
            let displayGroupId = groupId;
            const solutionMatch = groupId.match(/solution(\d+)/);
            if (solutionMatch) {
                const solutionNum = solutionMatch[1];
                displayGroupId = `Solution ${solutionNum}`;
            }
            
            html += `
                <div class="result-card">
                    <div class="card-header">
                        <h3>${displayGroupId}</h3>
                        <span class="similarity-score ${severityClass}">${similarity.toFixed(1)}% Similar</span>
                    </div>
                </div>
            `;
        });

        similarityResults.innerHTML = html;
    }
    
    // Display AI detection results
    function displayAIResults() {
        const aiData = resultData.results.ai_detection || {};
        const files = [];
    
        // Flatten out the nested structure: solution -> file -> details
        const flattenedResults = {};
    
        Object.keys(aiData).forEach(solution => {
            const fileMap = aiData[solution];
            Object.keys(fileMap).forEach(file => {
                files.push(file);
                const fileData = fileMap[file];
                // Use the pre-formatted values from the JSON
                const score = fileData.technical_score || 0;
                const likelihood = fileData.ai_likelihood || 'Unknown';
                const riskLevel = fileData.risk_level || 'Unknown';
    
                flattenedResults[file] = {
                    score: score,
                    likelihood: likelihood,
                    riskLevel: riskLevel
                };
            });
        });
    
        if (files.length === 0) {
            aiResults.innerHTML = '<div class="no-results">No AI-generated code detected.</div>';
            return;
        }
    
        let html = '';
    
        files.forEach(file => {
            const fileData = flattenedResults[file];
            const score = fileData.score || 0;
            const likelihood = fileData.likelihood || 'Unknown';
            const riskLevel = fileData.riskLevel || 'Unknown';
    
            // Extract student name from filename (format: studentname_solX.txt)
            let displayName = file;
            const solMatch = file.match(/(.+)_sol(\d+)\.txt$/);
            if (solMatch) {
                const studentName = solMatch[1];
                const solutionNum = solMatch[2];
                displayName = `${studentName} (Solution ${solutionNum})`;
            }
    
            let severityClass = 'low';
            if (riskLevel.toLowerCase().includes('high')) severityClass = 'high';
            else if (riskLevel.toLowerCase().includes('medium')) severityClass = 'medium';
    
            html += `
                <div class="result-card">
                    <div class="card-header">
                        <h3>${displayName}</h3>
                        <span class="ai-score ${severityClass}">${score.toFixed(1)}% (${riskLevel})</span>
                    </div>
                    <div class="card-body">
                        <p>This submission has a ${likelihood} likelihood of containing AI-generated code.</p>
                    </div>
                </div>
            `;
        });
    
        aiResults.innerHTML = html;
    }
    
    
    // Display web plagiarism results
    function displayWebResults() {
        const webData = resultData.results.web_plagiarism || {};
        const files = Object.keys(webData);
        
        if (files.length === 0) {
            webResults.innerHTML = '<div class="no-results">No web plagiarism detected.</div>';
            return;
        }
        
        let html = '';
        
        files.forEach(file => {
            const fileData = webData[file] || {};
            const matches = fileData.matches || [];
            
            // Extract student name from filename (format: studentname_solX.txt)
            let displayName = file;
            const solMatch = file.match(/(.+)_sol(\d+)\.txt$/);
            if (solMatch) {
                const studentName = solMatch[1];
                const solutionNum = solMatch[2];
                displayName = `${studentName} (Solution ${solutionNum})`;
            }
            
            if (matches.length === 0) {
                html += `
                    <div class="result-card">
                        <div class="card-header">
                            <h3>${displayName}</h3>
                            <span class="web-score low">No Matches</span>
                        </div>
                        <div class="card-body">
                            <p>No matches found with online sources.</p>
                        </div>
                    </div>
                `;
                return;
            }
            
            // Get highest similarity match
            let highestMatch = matches.reduce((prev, current) => 
                (prev.similarity > current.similarity) ? prev : current, { similarity: 0 });
            
            const highestSimilarity = highestMatch.similarity || 0;
            const severityClass = getSeverityClass(highestSimilarity * 100);
            
            html += `
                <div class="result-card">
                    <div class="card-header">
                        <h3>${displayName}</h3>
                        <span class="web-score ${severityClass}">${(highestSimilarity * 100).toFixed(1)}% Highest Match</span>
                    </div>
                    <div class="card-body">
                        <h4>Matching Sources:</h4>
                        <ul class="web-match-list">
                            ${matches.map(match => `
                                <li>
                                    <a href="${match.url}" target="_blank">${formatUrl(match.url)}</a>
                                    <span class="match-similarity">${(match.similarity * 100).toFixed(1)}%</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
            `;
        });
        
        webResults.innerHTML = html;
    }
    
    // Helper Functions
    function getSeverityClass(percentage) {
        if (percentage >= 70) return 'high';
        if (percentage >= 40) return 'medium';
        return 'low';
    }
    
    function formatUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname + urlObj.pathname.substring(0, 20) + (urlObj.pathname.length > 20 ? '...' : '');
        } catch (e) {
            return url.substring(0, 30) + (url.length > 30 ? '...' : '');
        }
    }
    
    function showLoading(isLoading) {
        loadingOverlay.style.display = isLoading ? 'flex' : 'none';
        
        if (isLoading) {
            errorOverlay.style.display = 'none';
        }
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorOverlay.style.display = 'flex';
        loadingOverlay.style.display = 'none';
        console.error(message);
    }
    
    // Start the application
    init();
}); 