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
    let allClusters = []; // Global variable to store clusters for modal access
    let solutionClusters = {}; // Map solution ID to its clusters
    
    // Make modal functions globally accessible
    window.expandCluster = function(event, clusterId) {
        // Prevent the click from bubbling up
        event.stopPropagation();
        
        // Get the modal elements
        const modal = document.getElementById('clusterModal');
        const modalContainer = modal.querySelector('.expanded-cluster-container');
        
        // Clear previous content
        modalContainer.innerHTML = '';
        
        // Get the solution group ID and cluster index
        const clusterElement = event.currentTarget.closest('.cluster');
        const solutionId = clusterElement.getAttribute('data-solution-id');
        const clusterIndex = parseInt(clusterElement.getAttribute('data-cluster-id'));
        
        // Create expanded view of the cluster
        const cluster = solutionClusters[solutionId]?.[clusterIndex];
        if (cluster) {
            // Set modal display style before appending content to prevent flickering
            modal.style.display = 'flex';
            
            // Add content after a short delay
            setTimeout(() => {
                renderExpandedCluster(cluster, modalContainer);
            }, 10);
        } else {
            console.error('Cluster not found:', solutionId, clusterIndex);
            return; // Don't show the modal if cluster not found
        }
        
        // Set up event handlers for the modal
        const closeBtn = modal.querySelector('.cluster-modal-close');
        closeBtn.onclick = function(e) {
            e.stopPropagation();
            modal.style.display = 'none';
        };
        
        // Close when clicking outside the modal content
        modal.onclick = function(e) {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };
        
        // Prevent click events from propagating
        modal.querySelector('.cluster-modal-content').onclick = function(e) {
            e.stopPropagation();
        };
    };
    
    // Make toggleSimilarityMatrix globally accessible
    window.toggleSimilarityMatrix = function(event) {
        event.preventDefault();
        const link = event.target;
        const container = link.parentElement.nextElementSibling;
        
        if (container.style.display === 'none') {
            container.style.display = 'block';
            link.textContent = 'Hide detailed similarity matrix';
        } else {
            container.style.display = 'none';
            link.textContent = 'View detailed similarity matrix';
        }
    };
    
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
        
        fetch(`http://127.0.0.1:5003/api/results/${sessionId}`)
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
        // Web plagiarism functionality removed
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
        
        if (Object.keys(similarityData).length === 0) {
            similarityResults.innerHTML = '<div class="no-results">Inadequate number of submissions provided to compare.</div>';
            return;
        }
        
        // Reset the solution clusters map
        solutionClusters = {};
        
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
            
            // Get high confidence and review pairs from the data
            const highConfidencePairs = groupData.high_confidence_pairs || [];
            const reviewPairs = groupData.needs_review_pairs || [];
            
            // If the data structure is different and we have all_suspicious_pairs instead
            const allPairs = [];
            if (!highConfidencePairs.length && !reviewPairs.length && groupData.all_suspicious_pairs) {
                // Try to extract data from the similarity_matrix format
                // First, we need the submission IDs
                const submissionIds = groupData.submission_ids || [];
                const matrix = groupData.similarity_matrix || groupData.tfidf_similarity_matrix || [];
                
                // Get high confidence pairs based on threshold
                const highThreshold = 0.7;
                const mediumThreshold = 0.4;
                const localHighConfidencePairs = [];
                const localReviewPairs = [];
                
                if (submissionIds.length > 0 && matrix.length > 0) {
                    // Create pairs from the matrix
                    for (let i = 0; i < submissionIds.length; i++) {
                        for (let j = i + 1; j < submissionIds.length; j++) {
                            const similarity = matrix[i][j];
                            const pair = {
                                pair: [submissionIds[i], submissionIds[j]],
                                similarity: similarity,
                                tfidf_similarity: similarity,
                                ast_similarity: similarity  // Use same value as fallback
                            };
                            
                            if (similarity >= highThreshold) {
                                localHighConfidencePairs.push(pair);
                            } else if (similarity >= mediumThreshold) {
                                localReviewPairs.push(pair);
                            }
                        }
                    }
                } else if (groupData.all_suspicious_pairs) {
                    // If we have all_suspicious_pairs, use that
                    groupData.all_suspicious_pairs.forEach(pairArray => {
                        // Find the similarity from the matrix if possible
                        let similarity = 0.5; // Default
                        const pair = {
                            pair: pairArray,
                            similarity: similarity,
                            tfidf_similarity: similarity,
                            ast_similarity: similarity
                        };
                        
                        // Try to find pair in the suspicious_pairs array which has similarity scores
                        if (groupData.suspicious_pairs) {
                            for (const suspiciousPair of groupData.suspicious_pairs) {
                                const [pairNames, pairSimilarity] = suspiciousPair;
                                if (pairNames[0] === pairArray[0] && pairNames[1] === pairArray[1] ||
                                    pairNames[0] === pairArray[1] && pairNames[1] === pairArray[0]) {
                                    similarity = pairSimilarity;
                                    pair.similarity = similarity;
                                    pair.tfidf_similarity = similarity;
                                    pair.ast_similarity = similarity;
                                    break;
                                }
                            }
                        }
                        
                        if (similarity >= highThreshold) {
                            localHighConfidencePairs.push(pair);
                        } else if (similarity >= mediumThreshold) {
                            localReviewPairs.push(pair);
                        }
                    });
                }
                
                // Use these local collections if the originals are empty
                if (localHighConfidencePairs.length > 0 || localReviewPairs.length > 0) {
                    // Sort by similarity (highest first)
                    localHighConfidencePairs.sort((a, b) => b.similarity - a.similarity);
                    localReviewPairs.sort((a, b) => b.similarity - a.similarity);
                }
                
                // Use our processed pairs
                const clusters = createClusters(
                    localHighConfidencePairs.length > 0 ? localHighConfidencePairs : highConfidencePairs,
                    localReviewPairs.length > 0 ? localReviewPairs : reviewPairs
                );
                
                // Store clusters for this solution
                solutionClusters[groupId] = clusters;
            
            html += `
                <div class="result-card">
                    <div class="card-header">
                        <h3>${displayGroupId}</h3>
                        <span class="similarity-score ${severityClass}">${similarity.toFixed(1)}% Similar</span>
                    </div>
                        <div class="card-body">
                            <div class="cluster-visualization">
                                ${renderClusters(clusters, groupId)}
                            </div>
                            ${localHighConfidencePairs.length > 0 ? `
                                <div class="high-confidence-section">
                                    <h4>High Confidence Matches</h4>
                                    <ul class="similarity-pair-list">
                                        ${localHighConfidencePairs.map(pair => `
                                            <li>
                                                <div class="pair-info">
                                                    <span class="file-names">${formatFileNames(pair.pair)}</span>
                                                    <span class="similarity-badge high">${(pair.similarity * 100).toFixed(1)}%</span>
                                                </div>
                                                <div class="similarity-details">
                                                    <span class="similarity-type">${getSimilarityTypeDescription(pair.tfidf_similarity, pair.ast_similarity)}</span>
                                                </div>
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                            ${localReviewPairs.length > 0 ? `
                                <div class="needs-review-section">
                                    <h4>Needs Review (Top ${Math.min(5, localReviewPairs.length)})</h4>
                                    <ul class="similarity-pair-list">
                                        ${localReviewPairs.slice(0, 5).map(pair => `
                                            <li>
                                                <div class="pair-info">
                                                    <span class="file-names">${formatFileNames(pair.pair)}</span>
                                                    <span class="similarity-badge medium">${(pair.similarity * 100).toFixed(1)}%</span>
                                                </div>
                                                <div class="similarity-details">
                                                    <span class="similarity-type">${getSimilarityTypeDescription(pair.tfidf_similarity, pair.ast_similarity)}</span>
                                                </div>
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                    </div>
                </div>
            `;
            } else {
                // We have the high confidence and needs review pairs directly
                const clusters = createClusters(highConfidencePairs, reviewPairs);
                
                // Store clusters for this solution
                solutionClusters[groupId] = clusters;
                
                html += `
                    <div class="result-card">
                        <div class="card-header">
                            <h3>${displayGroupId}</h3>
                            <span class="similarity-score ${severityClass}">${similarity.toFixed(1)}% Similar</span>
                        </div>
                        <div class="card-body">
                            <div class="cluster-visualization">
                                ${renderClusters(clusters, groupId)}
                            </div>
                            ${highConfidencePairs.length > 0 ? `
                                <div class="high-confidence-section">
                                    <h4>High Confidence Matches</h4>
                                    <ul class="similarity-pair-list">
                                        ${highConfidencePairs.map(pair => `
                                            <li>
                                                <div class="pair-info">
                                                    <span class="file-names">${formatFileNames(pair.pair)}</span>
                                                    <span class="similarity-badge high">${(pair.similarity * 100).toFixed(1)}%</span>
                                                </div>
                                                <div class="similarity-details">
                                                    <span class="similarity-type">${getSimilarityTypeDescription(pair.tfidf_similarity, pair.ast_similarity)}</span>
                                                </div>
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                            ${reviewPairs.length > 0 ? `
                                <div class="needs-review-section">
                                    <h4>Needs Review (Top ${Math.min(5, reviewPairs.length)})</h4>
                                    <ul class="similarity-pair-list">
                                        ${reviewPairs.slice(0, 5).map(pair => `
                                            <li>
                                                <div class="pair-info">
                                                    <span class="file-names">${formatFileNames(pair.pair)}</span>
                                                    <span class="similarity-badge medium">${(pair.similarity * 100).toFixed(1)}%</span>
                                                </div>
                                                <div class="similarity-details">
                                                    <span class="similarity-type">${getSimilarityTypeDescription(pair.tfidf_similarity, pair.ast_similarity)}</span>
                                                </div>
                                            </li>
                                        `).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }
        });

        similarityResults.innerHTML = html;
        
        // Initialize tooltips if needed
        initializeTooltips();
    }
    
    // Function to create clusters from similarity pairs
    function createClusters(highConfidencePairs, reviewPairs) {
        // Combine high confidence and top review pairs
        const allPairs = [...highConfidencePairs, ...reviewPairs.slice(0, 10)];
        
        // Create nodes (unique files)
        const nodes = new Set();
        allPairs.forEach(pair => {
            nodes.add(pair.pair[0]);
            nodes.add(pair.pair[1]);
        });
        
        // Create edges from pairs
        const edges = allPairs.map(pair => ({
            source: pair.pair[0],
            target: pair.pair[1],
            similarity: pair.similarity,
            type: pair.similarity >= 0.7 ? 'high' : 'medium'
        }));
        
        // Find connected components (basic clustering)
        const clusters = [];
        const nodeMap = new Map([...nodes].map(node => [node, { visited: false }]));
        
        // DFS to find connected components - this only builds the node groups
        function dfs(node, cluster) {
            const nodeData = nodeMap.get(node);
            if (nodeData.visited) return;
            
            nodeData.visited = true;
            cluster.nodes.push(node);
            
            // Just find all connected nodes to include in this cluster
            edges.forEach(edge => {
                if (edge.source === node && !nodeMap.get(edge.target).visited) {
                    dfs(edge.target, cluster);
                } else if (edge.target === node && !nodeMap.get(edge.source).visited) {
                    dfs(edge.source, cluster);
                }
            });
        }
        
        // Find all clusters - just group the nodes first
        for (const node of nodes) {
            if (!nodeMap.get(node).visited) {
                const cluster = { nodes: [], edges: [] };
                dfs(node, cluster);
                clusters.push(cluster);
            }
        }
        
        // Now add ALL edges between nodes in the same cluster
        for (const cluster of clusters) {
            // Create a set of nodes in this cluster for quick lookup
            const clusterNodeSet = new Set(cluster.nodes);
            
            // Add all edges where both ends are in this cluster
            edges.forEach(edge => {
                if (clusterNodeSet.has(edge.source) && clusterNodeSet.has(edge.target)) {
                    // Check if this edge is already in the cluster
                    const edgeExists = cluster.edges.some(e => 
                        (e.source === edge.source && e.target === edge.target) || 
                        (e.source === edge.target && e.target === edge.source)
                    );
                    
                    if (!edgeExists) {
                        cluster.edges.push(edge);
                    }
                }
            });
        }
        
        return clusters;
    }
    
    // Render an expanded version of the cluster in the modal
    function renderExpandedCluster(cluster, container) {
        // Create the expanded cluster element
        const expandedCluster = document.createElement('div');
        expandedCluster.className = 'expanded-cluster';
        container.appendChild(expandedCluster);
        
        // Add title with total similarities
        const titleEl = document.createElement('h4');
        titleEl.className = 'cluster-title';
        titleEl.textContent = `Cluster with ${cluster.nodes.length} submissions`;
        titleEl.style.position = 'absolute';
        titleEl.style.top = '10px';
        titleEl.style.left = '20px';
        
        // Add legend
        const legendEl = document.createElement('div');
        legendEl.className = 'similarity-legend';
        legendEl.innerHTML = `
            <div><span class="legend-marker high"></span> High Similarity (>70%)</div>
            <div><span class="legend-marker medium"></span> Medium Similarity (40-70%)</div>
        `;
        legendEl.style.position = 'absolute';
        legendEl.style.bottom = '10px';
        legendEl.style.right = '20px';
        
        // Add zoom controls
        const zoomControlsEl = document.createElement('div');
        zoomControlsEl.className = 'zoom-controls';
        zoomControlsEl.innerHTML = `
            <button class="zoom-in" title="Zoom In"><i class="fas fa-search-plus"></i></button>
            <button class="zoom-out" title="Zoom Out"><i class="fas fa-search-minus"></i></button>
            <button class="zoom-reset" title="Reset Zoom"><i class="fas fa-undo"></i></button>
        `;
        zoomControlsEl.style.position = 'absolute';
        zoomControlsEl.style.top = '10px';
        zoomControlsEl.style.right = '20px';
        
        // Create zoom container
        const zoomContainer = document.createElement('div');
        zoomContainer.className = 'zoom-container';
        zoomContainer.style.transform = 'scale(1)';
        zoomContainer.style.transformOrigin = 'center center';
        zoomContainer.style.transition = 'transform 0.3s ease';
        zoomContainer.style.width = '100%';
        zoomContainer.style.height = '100%';
        zoomContainer.style.position = 'relative';
        
        // First add the zoom container to the expanded cluster
        expandedCluster.appendChild(zoomContainer);
        
        // Then add the control elements (they will remain outside the zoom container)
        expandedCluster.appendChild(titleEl);
        expandedCluster.appendChild(legendEl);
        expandedCluster.appendChild(zoomControlsEl);
        
        // Set up zoom functionality
        let zoomLevel = 1;
        
        // Add zoom event listeners
        const zoomIn = zoomControlsEl.querySelector('.zoom-in');
        const zoomOut = zoomControlsEl.querySelector('.zoom-out');
        const zoomReset = zoomControlsEl.querySelector('.zoom-reset');
        
        zoomIn.addEventListener('click', () => {
            if (zoomLevel < 2) {
                zoomLevel += 0.25;
                zoomContainer.style.transform = `scale(${zoomLevel})`;
            }
        });
        
        zoomOut.addEventListener('click', () => {
            if (zoomLevel > 0.5) {
                zoomLevel -= 0.25;
                zoomContainer.style.transform = `scale(${zoomLevel})`;
            }
        });
        
        zoomReset.addEventListener('click', () => {
            zoomLevel = 1;
            zoomContainer.style.transform = 'scale(1)';
        });
        
        // Calculate optimal positions for nodes in a circular layout
        const nodeCount = cluster.nodes.length;
        const radius = Math.min(350, 120 + nodeCount * 30);
        const center = { x: radius, y: radius };
        
        // Create node elements with calculated positions
        const nodeElements = [];
        const nodePositions = [];
        
        // Create nodes
        cluster.nodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / nodeCount;
            const x = center.x + radius * 0.8 * Math.cos(angle);
            const y = center.y + radius * 0.8 * Math.sin(angle);
            
            const nodeEl = document.createElement('div');
            nodeEl.className = 'cluster-node';
            nodeEl.setAttribute('data-node-index', i);
            
            // Create more informative tooltip
            const solMatch = node.match(/(.+)_sol(\d+)\.txt$/);
            let tooltipText = node;
            if (solMatch) {
                const studentName = solMatch[1];
                const solutionNum = solMatch[2];
                tooltipText = `Student: ${studentName}\nSolution: ${solutionNum}`;
            }
            nodeEl.setAttribute('title', tooltipText);
            
            nodeEl.textContent = formatNodeName(node);
            nodeEl.style.position = 'absolute';
            nodeEl.style.left = `${x}px`;
            nodeEl.style.top = `${y}px`;
            nodeEl.style.transform = 'translate(-50%, -50%) scale(0)'; // Start small for animation
            
            // Important: Add node to the zoom container, not expandedCluster
            zoomContainer.appendChild(nodeEl);
            
            // Add animation for node appearance with delay based on index
            setTimeout(() => {
                nodeEl.style.transform = 'translate(-50%, -50%) scale(1)';
                nodeEl.style.transition = 'transform 0.3s ease-out';
            }, i * 50);
            
            nodeElements.push(nodeEl);
            nodePositions.push({ x, y });
        });
        
        // Create connection lines between nodes with animation delay
        cluster.edges.forEach((edge, edgeIndex) => {
            const sourceIdx = cluster.nodes.indexOf(edge.source);
            const targetIdx = cluster.nodes.indexOf(edge.target);
            
            if (sourceIdx !== -1 && targetIdx !== -1) {
                const sourcePos = nodePositions[sourceIdx];
                const targetPos = nodePositions[targetIdx];
                
                const connEl = document.createElement('div');
                connEl.className = `node-connection ${edge.type}`;
                connEl.setAttribute('data-source', sourceIdx);
                connEl.setAttribute('data-target', targetIdx);
                connEl.setAttribute('title', `${formatFileNames([cluster.nodes[sourceIdx], cluster.nodes[targetIdx]])}: ${(edge.similarity * 100).toFixed(1)}%`);
                
                // Calculate line properties
                const dx = targetPos.x - sourcePos.x;
                const dy = targetPos.y - sourcePos.y;
                const length = Math.sqrt(dx * dx + dy * dy);
                const angle = Math.atan2(dy, dx) * (180 / Math.PI);
                
                // Apply properties to the connection element
                connEl.style.position = 'absolute';
                connEl.style.width = `0px`; // Start with zero width for animation
                connEl.style.left = `${sourcePos.x}px`;
                connEl.style.top = `${sourcePos.y}px`;
                connEl.style.transformOrigin = '0 0';
                connEl.style.transform = `rotate(${angle}deg)`;
                
                // Important: Add the connection to the zoom container
                zoomContainer.appendChild(connEl);
                
                // Animation delay based on node appearance
                setTimeout(() => {
                    connEl.style.width = `${length}px`;
                    connEl.style.transition = 'width 0.5s ease-out';
                }, (Math.max(sourceIdx, targetIdx) + 1) * 50);
                
                // Connection label with similarity percentage
                const labelEl = document.createElement('div');
                labelEl.className = 'connection-label';
                labelEl.textContent = `${(edge.similarity * 100).toFixed(0)}%`;
                labelEl.style.position = 'absolute';
                labelEl.style.left = `${sourcePos.x + dx/2}px`;
                labelEl.style.top = `${sourcePos.y + dy/2}px`;
                labelEl.style.transform = 'translate(-50%, -50%) scale(0)'; // Start small for animation
                
                // Important: Add the label to the zoom container
                zoomContainer.appendChild(labelEl);
                
                // Animate label appearance
                setTimeout(() => {
                    labelEl.style.transform = 'translate(-50%, -50%) scale(1)';
                    labelEl.style.transition = 'transform 0.3s ease-out';
                }, (Math.max(sourceIdx, targetIdx) + 1) * 50 + 200);
            }
        });
        
        // Add interaction to highlight connections after all elements are added
        nodeElements.forEach((nodeEl, i) => {
            nodeEl.addEventListener('mouseenter', () => highlightConnections(i));
            nodeEl.addEventListener('mouseleave', () => resetHighlights());
        });
        
        // Function to highlight connections for a specific node
        function highlightConnections(nodeIndex) {
            // Dim all nodes and connections
            zoomContainer.querySelectorAll('.cluster-node').forEach(node => {
                node.style.opacity = '0.4';
            });
            zoomContainer.querySelectorAll('.node-connection').forEach(conn => {
                conn.style.opacity = '0.2';
            });
            zoomContainer.querySelectorAll('.connection-label').forEach(label => {
                label.style.opacity = '0.2';
            });
            
            // Highlight the selected node
            nodeElements[nodeIndex].style.opacity = '1';
            
            // Highlight connected nodes and their connections
            zoomContainer.querySelectorAll('.node-connection').forEach(conn => {
                const sourceIdx = parseInt(conn.getAttribute('data-source'));
                const targetIdx = parseInt(conn.getAttribute('data-target'));
                
                if (sourceIdx === nodeIndex || targetIdx === nodeIndex) {
                    // Highlight connected node
                    if (sourceIdx === nodeIndex) {
                        nodeElements[targetIdx].style.opacity = '1';
                    } else {
                        nodeElements[sourceIdx].style.opacity = '1';
                    }
                    
                    // Highlight connection
                    conn.style.opacity = '1';
                    
                    // Find and highlight the label (which might be the next sibling)
                    const connRect = conn.getBoundingClientRect();
                    const labels = zoomContainer.querySelectorAll('.connection-label');
                    labels.forEach(label => {
                        const labelRect = label.getBoundingClientRect();
                        // Find the label that's positioned along this connection
                        if (Math.abs(labelRect.left - (connRect.left + connRect.width/2)) < 50 &&
                            Math.abs(labelRect.top - (connRect.top + connRect.height/2)) < 50) {
                            label.style.opacity = '1';
                        }
                    });
                }
            });
        }
        
        // Function to reset highlighting
        function resetHighlights() {
            zoomContainer.querySelectorAll('.cluster-node, .node-connection, .connection-label').forEach(el => {
                el.style.opacity = '1';
            });
        }
    }
    
    // Function to render the clusters visually
    function renderClusters(clusters, solutionId) {
        if (clusters.length === 0) return '';
        
        return `
            <div class="clusters-container">
                ${clusters.map((cluster, i) => {
                    // Create visual connections between nodes
                    const connections = [];
                    cluster.edges.forEach(edge => {
                        const sourceNode = cluster.nodes.indexOf(edge.source);
                        const targetNode = cluster.nodes.indexOf(edge.target);
                        if (sourceNode !== -1 && targetNode !== -1) {
                            connections.push({
                                source: sourceNode,
                                target: targetNode,
                                type: edge.type,
                                similarity: edge.similarity
                            });
                        }
                    });
                    
                    return `
                    <div class="cluster" data-cluster-id="${i}" data-solution-id="${solutionId}">
                        <div class="cluster-files-summary" onclick="expandCluster(event, ${i})">
                            <h4 class="cluster-title-mini">Cluster with ${cluster.nodes.length} submissions</h4>
                            <div class="cluster-files-list">
                                ${cluster.nodes.map(node => `
                                    <div class="cluster-file-item" title="${node}">
                                        ${formatNodeName(node)}
                    </div>
                                `).join('')}
                    </div>
                        </div>
                        <div class="cluster-expand-hint">Click to expand and view connections</div>
                </div>
            `;
                }).join('')}
            </div>
            ${clusters.length > 0 && clusters[0].nodes.length > 3 ? 
                `<div class="view-details-link"><a href="#" onclick="toggleSimilarityMatrix(event)">View detailed similarity matrix</a></div>
                 <div class="similarity-matrix-container" style="display: none;">
                    ${renderSimilarityMatrix(clusters)}
                 </div>` 
                : ''}
        `;
    }
    
    // Helper function to count connections for a node
    function countConnections(connections, nodeIndex) {
        return connections.filter(conn => conn.source === nodeIndex || conn.target === nodeIndex).length;
    }
    
    // Function to render a similarity matrix for better visualization
    function renderSimilarityMatrix(clusters) {
        // Combine all nodes from all clusters
        const allNodes = new Set();
        const allEdges = [];
        
        clusters.forEach(cluster => {
            cluster.nodes.forEach(node => allNodes.add(node));
            cluster.edges.forEach(edge => allEdges.push(edge));
        });
        
        const nodes = Array.from(allNodes);
        
        // Create a similarity matrix - initialize with zeros
        const matrix = [];
        for (let i = 0; i < nodes.length; i++) {
            matrix.push(new Array(nodes.length).fill(0));
            matrix[i][i] = 1; // Self-similarity is always 1
        }
        
        // Fill in the matrix with similarity values
        allEdges.forEach(edge => {
            const i = nodes.indexOf(edge.source);
            const j = nodes.indexOf(edge.target);
            if (i !== -1 && j !== -1) {
                matrix[i][j] = edge.similarity;
                matrix[j][i] = edge.similarity; // Symmetric matrix
            }
        });
        
        // Generate the HTML for the matrix visualization
        let html = `<table class="similarity-matrix">`;
        
        // Header row with shortened node names
        html += `<tr><th></th>`;
        nodes.forEach(node => {
            html += `<th title="${node}">${formatNodeName(node)}</th>`;
        });
        html += `</tr>`;
        
        // Data rows
        nodes.forEach((rowNode, i) => {
            html += `<tr>`;
            html += `<th title="${rowNode}">${formatNodeName(rowNode)}</th>`;
            
            matrix[i].forEach((value, j) => {
                const cellClass = value >= 0.7 ? 'high' : (value >= 0.4 ? 'medium' : 'low');
                html += `<td class="${cellClass}" title="${rowNode} & ${nodes[j]}: ${(value * 100).toFixed(1)}%">
                    ${(value * 100).toFixed(0)}%
                </td>`;
            });
            
            html += `</tr>`;
        });
        
        html += `</table>`;
        return html;
    }
    
    // Format node name to be more readable
    function formatNodeName(filename) {
        // Extract student name or shorter version of filename
        const solMatch = filename.match(/(.+)_sol(\d+)\.txt$/);
        if (solMatch) {
            const studentName = solMatch[1];
            // Just return the first part to keep it short
            return studentName.split(/[_\s]/)[0];
        }
        // If no match, just take the first part of the filename
        return filename.split('.')[0].substring(0, 6);
    }
    
    // Format file names for display
    function formatFileNames(fileNames) {
        return fileNames.map(file => {
            const solMatch = file.match(/(.+)_sol(\d+)\.txt$/);
            if (solMatch) {
                const studentName = solMatch[1];
                const solutionNum = solMatch[2];
                return `${studentName}`;
            }
            return file;
        }).join(' & ');
    }
    
    // Initialize tooltips if needed
    function initializeTooltips() {
        // This could be replaced with actual tooltip library initialization
        const tooltipElements = document.querySelectorAll('[title]');
        // Add basic tooltip functionality if needed
        
        // Position connection lines
        positionConnectionLines();
    }
    
    // Position connection lines between nodes
    function positionConnectionLines() {
        // Wait for DOM to be fully rendered
        setTimeout(() => {
            document.querySelectorAll('.cluster').forEach(cluster => {
                const nodes = cluster.querySelectorAll('.cluster-node');
                const connections = cluster.querySelectorAll('.node-connection');
                
                // Get node positions
                const nodePositions = [];
                nodes.forEach(node => {
                    const rect = node.getBoundingClientRect();
                    const clusterRect = cluster.getBoundingClientRect();
                    
                    nodePositions.push({
                        left: rect.left - clusterRect.left + rect.width / 2,
                        top: rect.top - clusterRect.top + rect.height / 2,
                        width: rect.width,
                        height: rect.height,
                        node: node
                    });
                });
                
                // Position each connection line
                connections.forEach(conn => {
                    // Get the source and target node indices
                    const sourceIndex = parseInt(conn.getAttribute('data-source') || '0');
                    const targetIndex = parseInt(conn.getAttribute('data-target') || '0');
                    
                    if (sourceIndex < nodePositions.length && targetIndex < nodePositions.length) {
                        positionConnection(conn, nodePositions[sourceIndex], nodePositions[targetIndex]);
                    }
                });
                
                // If there are many connections, adjust node positions slightly to minimize overlap
                if (connections.length > nodePositions.length * 1.5) {
                    adjustNodePositions(cluster, nodePositions);
                    
                    // Reposition connections after node adjustments
                    setTimeout(() => {
                        connections.forEach(conn => {
                            const sourceIndex = parseInt(conn.getAttribute('data-source') || '0');
                            const targetIndex = parseInt(conn.getAttribute('data-target') || '0');
                            
                            if (sourceIndex < nodePositions.length && targetIndex < nodePositions.length) {
                                // Get updated positions after DOM changes
                                const sourceNode = nodes[sourceIndex];
                                const targetNode = nodes[targetIndex];
                                
                                const sourceRect = sourceNode.getBoundingClientRect();
                                const targetRect = targetNode.getBoundingClientRect();
                                const clusterRect = cluster.getBoundingClientRect();
                                
                                const sourcePos = {
                                    left: sourceRect.left - clusterRect.left + sourceRect.width / 2,
                                    top: sourceRect.top - clusterRect.top + sourceRect.height / 2
                                };
                                
                                const targetPos = {
                                    left: targetRect.left - clusterRect.left + targetRect.width / 2,
                                    top: targetRect.top - clusterRect.top + targetRect.height / 2
                                };
                                
                                positionConnection(conn, sourcePos, targetPos);
                            }
                        });
                    }, 50);
                }
            });
        }, 100);
    }
    
    // Adjust node positions to minimize connection overlap
    function adjustNodePositions(cluster, nodePositions) {
        const clusterWidth = cluster.clientWidth;
        const clusterHeight = cluster.clientHeight;
        
        // Move nodes slightly to create a more circular layout
        nodePositions.forEach((pos, i) => {
            const node = pos.node;
            const numNodes = nodePositions.length;
            
            // Calculate a position in a circular arrangement
            const angle = (2 * Math.PI * i) / numNodes;
            const radius = Math.min(clusterWidth, clusterHeight) * 0.35;
            const centerX = clusterWidth / 2;
            const centerY = clusterHeight / 2;
            
            // New position
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            
            // Apply new position with a transition for smooth movement
            node.style.transition = 'transform 0.5s ease-out';
            node.style.position = 'absolute';
            node.style.left = x + 'px';
            node.style.top = y + 'px';
            node.style.transform = 'translate(-50%, -50%)';
        });
    }
    
    // Position a single connection line between two nodes
    function positionConnection(connElement, sourcePos, targetPos) {
        // Calculate the angle and length
        const dx = targetPos.left - sourcePos.left;
        const dy = targetPos.top - sourcePos.top;
        const length = Math.sqrt(dx * dx + dy * dy);
        const angle = Math.atan2(dy, dx) * (180 / Math.PI);
        
        // Apply transforms
        connElement.style.width = `${length}px`;
        connElement.style.left = `${sourcePos.left}px`;
        connElement.style.top = `${sourcePos.top}px`;
        connElement.style.transform = `rotate(${angle}deg)`;
    }
    
    // Display AI detection results
    function displayAIResults() {
        const aiData = resultData.results.ai_detection || {};
        
        if (!aiData || Object.keys(aiData).length === 0) {
            aiResults.innerHTML = '<div class="no-results">No AI detection results available.</div>';
            return;
        }
        
        // Organize data by solution first
        const solutionGroups = {};
        
        // Process all solutions and organize by solution
        Object.entries(aiData).forEach(([solutionKey, solutionFiles]) => {
            // Extract the solution number
            const solutionMatch = solutionKey.match(/solution(\d+)/);
            const solutionNum = solutionMatch ? solutionMatch[1] : solutionKey;
            const displaySolutionName = `Solution ${solutionNum}`;
            
            // Create solution group if it doesn't exist
            if (!solutionGroups[solutionKey]) {
                solutionGroups[solutionKey] = {
                    name: displaySolutionName,
                    items: [],
                    highRiskCount: 0,
                    mediumRiskCount: 0,
                    lowRiskCount: 0,
                    avgScore: 0
                };
            }
            
            // Add all files to this solution
            Object.entries(solutionFiles).forEach(([filename, fileData]) => {
                const technicalScore = fileData.technical_score || 0;
                const aiLikelihood = fileData.ai_likelihood || "0%";
                const riskLevel = fileData.risk_level || "Unknown";
                const likelihoodValue = parseInt(aiLikelihood, 10) || 0;
                const topIndicators = fileData.top_indicators || [];
                const detailedResults = fileData.detailed_results || {};
                
                // Extract student name from filename
                const solMatch = filename.match(/(.+)_sol(\d+)\.txt$/);
                const studentName = solMatch ? solMatch[1] : filename.split('.')[0];
                const fileSolutionNum = solMatch ? solMatch[2] : '';
                
                // Create item with relevant data
                const item = {
                    filename,
                    studentName,
                    solutionNum: fileSolutionNum,
                    likelihoodValue,
                    technicalScore,
                    riskLevel,
                    topIndicators,
                    detailedResults
                };
                
                // Add to solution group
                solutionGroups[solutionKey].items.push(item);
                
                // Update risk counts
                if (riskLevel.includes("HIGH") || riskLevel.includes("CRITICAL")) {
                    solutionGroups[solutionKey].highRiskCount++;
                    item.riskClass = 'high';
                } else if (riskLevel.includes("MEDIUM") || riskLevel.includes("MODERATE")) {
                    solutionGroups[solutionKey].mediumRiskCount++;
                    item.riskClass = 'medium';
                } else {
                    solutionGroups[solutionKey].lowRiskCount++;
                    item.riskClass = 'low';
                }
            });
            
            // Calculate average score for the solution
            if (solutionGroups[solutionKey].items.length > 0) {
                const totalScore = solutionGroups[solutionKey].items.reduce((sum, item) => sum + item.likelihoodValue, 0);
                solutionGroups[solutionKey].avgScore = Math.round(totalScore / solutionGroups[solutionKey].items.length);
            }
            
            // Sort items by likelihood (highest first)
            solutionGroups[solutionKey].items.sort((a, b) => b.likelihoodValue - a.likelihoodValue);
        });
        
        // If no items to display
        if (Object.keys(solutionGroups).length === 0) {
            aiResults.innerHTML = `
                <div class="no-suspicious-submissions">
                    <i class="fas fa-check-circle"></i>
                    <h3>No AI Detection Results</h3>
                    <p>No submissions were analyzed for AI-generated content.</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="ai-solution-groups">';
        
        // Render each solution
        Object.entries(solutionGroups).forEach(([solutionKey, solutionGroup]) => {
            // Calculate severity class based on risk counts
            let severityClass = 'low';
            if (solutionGroup.highRiskCount > 0) {
                severityClass = 'high';
            } else if (solutionGroup.mediumRiskCount > 0) {
                severityClass = 'medium';
            }
            
            // Create risk summary
            const riskSummary = [];
            if (solutionGroup.highRiskCount > 0) {
                riskSummary.push(`<span class="risk-count high">${solutionGroup.highRiskCount} High</span>`);
            }
            if (solutionGroup.mediumRiskCount > 0) {
                riskSummary.push(`<span class="risk-count medium">${solutionGroup.mediumRiskCount} Medium</span>`);
            }
            if (solutionGroup.lowRiskCount > 0) {
                riskSummary.push(`<span class="risk-count low">${solutionGroup.lowRiskCount} Low</span>`);
            }
    
                html += `
                <div class="ai-solution-card ${severityClass}">
                        <div class="card-header">
                        <h3>${solutionGroup.name}</h3>
                        <div class="ai-risk-summary">
                            ${riskSummary.join(' ')}
                            <span class="ai-score ${severityClass}">${solutionGroup.avgScore}% Avg</span>
                        </div>
                        </div>
                        <div class="card-body">
                        <div class="ai-cluster-visualization">
                            ${renderAISolutionButtons(solutionGroup.items, solutionKey)}
                        </div>
                        <div class="ai-cluster-hint-text">Click on a student button to see detailed analysis</div>
                        </div>
                    </div>
                `;
        });
        
        html += '</div>';
        
        // Create a modal for expanded view
        html += `
            <div id="aiClusterModal" class="cluster-modal">
                <div class="cluster-modal-content">
                    <span class="cluster-modal-close">&times;</span>
                    <h3>AI Detection Details</h3>
                    <div class="expanded-ai-container"></div>
                </div>
            </div>
        `;
    
        aiResults.innerHTML = html;
        
        // Set up modal close functionality
        const aiModal = document.getElementById('aiClusterModal');
        const closeBtn = aiModal.querySelector('.cluster-modal-close');
        
        closeBtn.onclick = function(e) {
            e.stopPropagation();
            aiModal.style.display = 'none';
        };
        
        aiModal.onclick = function(e) {
            if (e.target === aiModal) {
                aiModal.style.display = 'none';
            }
        };
    }
    
    // Render AI buttons for a solution
    function renderAISolutionButtons(items, solutionKey) {
        if (!items.length) return '';
        
        return `
            <div class="ai-clusters-grid">
                ${items.map((item, index) => `
                    <div class="ai-cluster-button ${item.riskClass}" onclick="expandAICluster(event, '${solutionKey}', ${index})">
                        <span class="ai-student-name">${item.studentName}</span>
                        <span class="ai-button-likelihood">${item.likelihoodValue}%</span>
                        <i class="fas fa-expand-alt expand-icon" title="Click to see detailed analysis"></i>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    // Create expandable AI detection clusters
    window.expandAICluster = function(event, solutionKey, index) {
        // Prevent the click from bubbling up
        event.stopPropagation();
        
        // Get the modal and container
        const modal = document.getElementById('aiClusterModal');
        const container = modal.querySelector('.expanded-ai-container');
        
        // Clear previous content
        container.innerHTML = '';
        
        // Get the solution's items
        const aiData = resultData.results.ai_detection || {};
        const solutionData = aiData[solutionKey] || {};
        
        // Convert to array of items
        const allItems = [];
        Object.entries(solutionData).forEach(([filename, fileData]) => {
            const technicalScore = fileData.technical_score || 0;
            const aiLikelihood = fileData.ai_likelihood || "0%";
            const riskLevel = fileData.risk_level || "Unknown";
            const likelihoodValue = parseInt(aiLikelihood, 10) || 0;
            const topIndicators = fileData.top_indicators || [];
            const detailedResults = fileData.detailed_results || {};
            
            const solMatch = filename.match(/(.+)_sol(\d+)\.txt$/);
            const studentName = solMatch ? solMatch[1] : filename.split('.')[0];
            const solutionNum = solMatch ? solMatch[2] : '';
            
            // Determine risk class
            let riskClass = 'low';
            if (riskLevel.includes("HIGH") || riskLevel.includes("CRITICAL")) {
                riskClass = 'high';
            } else if (riskLevel.includes("MEDIUM") || riskLevel.includes("MODERATE")) {
                riskClass = 'medium';
            }
            
            allItems.push({
                filename,
                studentName,
                solutionNum,
                likelihoodValue,
                technicalScore,
                riskLevel,
                topIndicators,
                detailedResults,
                riskClass
            });
        });
        
        // Sort by likelihood (highest first)
        allItems.sort((a, b) => b.likelihoodValue - a.likelihoodValue);
        
        // Get the item at the specified index
        const item = allItems[index];
        if (!item) {
            console.error("Item not found at index:", index);
                return;
            }
            
        // Set modal display style
        modal.style.display = 'flex';
        
        // Create the detailed view HTML
        const detailedHtml = `
            <div class="ai-detailed-analysis ${item.riskClass}">
                <div class="ai-detail-header">
                    <h4>${item.studentName} (Solution ${item.solutionNum})</h4>
                    <div class="ai-detail-meta">
                        <div class="ai-detail-score">${item.likelihoodValue}% AI Likelihood</div>
                        <div class="ai-detail-risk">${item.riskLevel}</div>
                    </div>
                </div>
                
                <div class="ai-indicators-section">
                    <h5>AI Detection Indicators</h5>
                    <div class="ai-indicators-grid">
                        ${Object.entries(item.detailedResults).map(([key, value]) => {
                            // Skip overall score and domain/educational patterns
                            if (key === 'overall_score' || key === 'domain_patterns_score' || key === 'educational_patterns_score') return ''; 
                            const formattedName = formatIndicatorName(key);
                            const percentage = Math.round(value * 100);
                            const indicatorClass = percentage >= 70 ? 'high' : (percentage >= 40 ? 'medium' : 'low');
                            
                            return `
                                <div class="ai-indicator-card ${indicatorClass}">
                                    <div class="indicator-name">${formattedName}</div>
                                    <div class="indicator-meter">
                                        <div class="indicator-track">
                                            <div class="indicator-fill ${indicatorClass}" style="width: ${percentage}%"></div>
                    </div>
                                        <div class="indicator-value">${percentage}%</div>
                    </div>
                </div>
            `;
                        }).join('')}
                    </div>
                </div>
                
                <div class="ai-interpretation">
                    <h5>Interpretation</h5>
                    <div class="interpretation-content">
                        <p>
                            This submission has been analyzed for AI-generated content with a resulting likelihood of ${item.likelihoodValue}%.
                            ${getInterpretationText(item)}
                        </p>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = detailedHtml;
    };
    
    // Get interpretation text based on item data
    function getInterpretationText(item) {
        // Find top two indicators, excluding domain and educational patterns
        const indicators = Object.entries(item.detailedResults)
            .filter(([key]) => key !== 'overall_score' && key !== 'domain_patterns_score' && key !== 'educational_patterns_score')
            .sort((a, b) => b[1] - a[1])
            .slice(0, 2);
        
        if (indicators.length === 0) return "";
        
        const topIndicator = indicators[0];
        const topName = formatIndicatorName(topIndicator[0]);
        const topValue = Math.round(topIndicator[1] * 100);
        
        let text = `The strongest indicator is <strong>${topName} (${topValue}%)</strong>, `;
        
        if (topName.includes("Formatting")) {
            text += "which suggests consistent code style and formatting often associated with AI-generated code.";
        } else if (topName.includes("Code Structure")) {
            text += "which indicates structured patterns in the code that can be characteristic of AI generation.";
        } else if (topName.includes("Similarity")) {
            text += "which identifies patterns similar to known AI-generated code examples.";
        } else if (topName.includes("ML Prediction")) {
            text += "based on machine learning model prediction of AI-generated content.";
        } else {
            text += "which is a significant factor in determining AI-generated content.";
        }
        
        return text;
    }
    
    // Helper function to format indicator names for display
    function formatIndicatorName(name) {
        // Convert snake_case to readable text
        if (!name) return '';
        return name.replace(/_score$/, '')
                  .replace(/_/g, ' ')
                  .split(' ')
                  .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ');
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
    
    // Function to determine similarity type based on TF-IDF and AST percentages
    function getSimilarityTypeDescription(tfidfSim, astSim) {
        const tfidfPercentage = tfidfSim * 100;
        const astPercentage = astSim * 100;
        
        // High structural and textual similarity
        if (astPercentage >= 70 && tfidfPercentage >= 70) {
            return "High structural and textual similarity";
        }
        // High structural similarity
        else if (astPercentage >= 70 && tfidfPercentage < 70) {
            return "High structural similarity with different variable names";
        }
        // High textual similarity
        else if (tfidfPercentage >= 70 && astPercentage < 40) {
            return "High textual similarity with different structure";
        }
        // Medium similarity in both
        else if (tfidfPercentage >= 40 && astPercentage >= 40) {
            return "Medium similarity in both structure and text";
        }
        // Medium textual, low structural
        else if (tfidfPercentage >= 40 && astPercentage < 40) {
            return "Medium textual similarity with different structure";
        }
        // Medium structural, low textual
        else if (astPercentage >= 40 && tfidfPercentage < 40) {
            return "Similar structure with different implementation";
        }
        // Low in both
        else {
            return "Low similarity";
        }
    }
    
    // Start the application
    init();
}); 