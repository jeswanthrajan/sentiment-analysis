// Dashboard JavaScript for Brand Sentiment Monitor

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initSidebar();
    initNavigation();
    initDateRangePicker();
    initBrandSelector();
    initCharts();
    initWordCloud();
    initFilters();
    initModals();
    initFileUpload();
    loadRecentUploads();
});
 

/**
 * Initialize sidebar functionality
 */
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('#sidebarToggle');
    const mainContent = document.querySelector('.main-content');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');

            // Create overlay for mobile
            if (window.innerWidth < 992) {
                if (sidebar.classList.contains('expanded')) {
                    sidebar.classList.remove('expanded');
                    document.querySelector('.overlay').remove();
                } else {
                    sidebar.classList.add('expanded');
                    const overlay = document.createElement('div');
                    overlay.classList.add('overlay');
                    document.body.appendChild(overlay);

                    overlay.addEventListener('click', function() {
                        sidebar.classList.remove('expanded');
                        overlay.remove();
                    });
                }
            }
        });
    }

    // Handle responsive sidebar
    window.addEventListener('resize', function() {
        if (window.innerWidth < 992) {
            sidebar.classList.add('collapsed');
        }
    });

    // Initial check for mobile
    if (window.innerWidth < 992) {
        sidebar.classList.add('collapsed');
    }
}

/**
 * Initialize navigation functionality
 */
function initNavigation() {
    const navLinks = document.querySelectorAll('.sidebar-menu li a');
    const sections = document.querySelectorAll('.content-section');
    const sectionTitle = document.querySelector('#sectionTitle');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Update active link
            navLinks.forEach(link => link.parentElement.classList.remove('active'));
            this.parentElement.classList.add('active');

            // Show corresponding section
            const targetSection = this.getAttribute('href').substring(1);
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === targetSection) {
                    section.classList.add('active');
                    if (sectionTitle) {
                        sectionTitle.textContent = this.textContent.trim();
                    }
                }
            });

            // Close sidebar on mobile
            if (window.innerWidth < 992) {
                document.querySelector('.sidebar').classList.remove('expanded');
                const overlay = document.querySelector('.overlay');
                if (overlay) {
                    overlay.remove();
                }
            }
        });
    });
}

/**
 * Initialize date range picker
 */
function initDateRangePicker() {
    const dateRangeInput = document.querySelector('#dateRange');

    if (dateRangeInput && typeof $.fn.daterangepicker !== 'undefined') {
        $(dateRangeInput).daterangepicker({
            startDate: moment().subtract(7, 'days'),
            endDate: moment(),
            ranges: {
                'Today': [moment(), moment()],
                'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
                'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                'This Month': [moment().startOf('month'), moment().endOf('month')],
                'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
            }
        }, function(start, end, label) {
            // Update charts and data when date range changes
            updateDashboardData(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'));
        });
    }
}

/**
 * Initialize brand selector
 */
function initBrandSelector() {
    const brandSelector = document.querySelector('#brandSelector');

    if (brandSelector) {
        brandSelector.addEventListener('change', function() {
            const selectedBrand = this.value;

            if (selectedBrand === 'add') {
                // Show add brand modal
                const addBrandModal = new bootstrap.Modal(document.getElementById('addBrandModal'));
                addBrandModal.show();

                // Reset selector to previous value
                this.value = this.getAttribute('data-previous-value') || 'mybrand';
            } else {
                // Save current value
                this.setAttribute('data-previous-value', selectedBrand);

                // Update dashboard data for selected brand
                updateDashboardData();
            }
        });
    }

    // Add brand form submission
    const saveBrandBtn = document.querySelector('#saveBrandBtn');
    if (saveBrandBtn) {
        saveBrandBtn.addEventListener('click', function() {
            const brandName = document.querySelector('#brandName').value;
            const brandKeywords = document.querySelector('#brandKeywords').value;

            if (!brandName) {
                alert('Please enter a brand name');
                return;
            }

            // Get selected platforms
            const platforms = [];
            document.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                platforms.push(checkbox.value);
            });

            // In a real implementation, this would send data to the server
            console.log('Adding brand:', {
                name: brandName,
                keywords: brandKeywords.split(',').map(k => k.trim()),
                platforms: platforms
            });

            // Close modal
            const addBrandModal = bootstrap.Modal.getInstance(document.getElementById('addBrandModal'));
            addBrandModal.hide();

            // Add brand to selector
            const option = document.createElement('option');
            option.value = brandName.toLowerCase().replace(/\s+/g, '');
            option.textContent = brandName;

            const addOption = brandSelector.querySelector('option[value="add"]');
            brandSelector.insertBefore(option, addOption);
            brandSelector.value = option.value;

            // Update dashboard
            updateDashboardData();
        });
    }
}

/**
 * Initialize charts
 */
function initCharts() {
    // Chart data for different time periods
    const chartData = {
        week: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            positive: [65, 70, 68, 75, 80, 82, 85],
            neutral: [25, 20, 22, 15, 12, 10, 8],
            negative: [10, 10, 10, 10, 8, 8, 7]
        },
        month: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            positive: [72, 75, 78, 82],
            neutral: [18, 15, 14, 10],
            negative: [10, 10, 8, 8]
        },
        quarter: {
            labels: ['Jan', 'Feb', 'Mar'],
            positive: [68, 75, 82],
            neutral: [22, 15, 10],
            negative: [10, 10, 8]
        }
    };

    // Sentiment Trend Chart
    const sentimentTrendCtx = document.getElementById('sentimentTrendChart');
    let sentimentTrendChart;

    if (sentimentTrendCtx) {
        sentimentTrendChart = new Chart(sentimentTrendCtx, {
            type: 'line',
            data: {
                labels: chartData.week.labels,
                datasets: [
                    {
                        label: 'Positive',
                        data: chartData.week.positive,
                        borderColor: '#4cc9a0',
                        backgroundColor: 'rgba(76, 201, 160, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Neutral',
                        data: chartData.week.neutral,
                        borderColor: '#8d99ae',
                        backgroundColor: 'rgba(141, 153, 174, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Negative',
                        data: chartData.week.negative,
                        borderColor: '#f72585',
                        backgroundColor: 'rgba(247, 37, 133, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });

        // Handle period buttons
        document.querySelectorAll('.chart-card-header [data-period]').forEach(button => {
            button.addEventListener('click', function() {
                // Update active button
                document.querySelectorAll('.chart-card-header [data-period]').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');

                // Update chart data based on period
                const period = this.getAttribute('data-period');
                updateSentimentTrendChart(sentimentTrendChart, period);
            });
        });
    }

    // Sentiment Distribution Chart
    const sentimentDistributionCtx = document.getElementById('sentimentDistributionChart');
    if (sentimentDistributionCtx) {
        const sentimentDistributionChart = new Chart(sentimentDistributionCtx, {
            type: 'doughnut',
            data: {
                labels: ['Positive', 'Neutral', 'Negative'],
                datasets: [{
                    data: [68, 20, 12],
                    backgroundColor: [
                        '#28a745',
                        '#6c757d',
                        '#dc3545'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                },
                cutout: '70%'
            }
        });
    }

    // Add event listeners to chart period buttons
    const chartPeriodButtons = document.querySelectorAll('.chart-actions .btn');
    chartPeriodButtons.forEach(button => {
        button.addEventListener('click', function() {
            const period = this.getAttribute('data-period');
            const chartContainer = this.closest('.chart-card').querySelector('.chart-card-body canvas');
            const chartId = chartContainer.id;

            // Remove active class from all buttons in this chart card
            this.closest('.chart-actions').querySelectorAll('.btn').forEach(btn => {
                btn.classList.remove('active');
            });

            // Add active class to clicked button
            this.classList.add('active');

            // Update chart data based on period
            if (chartId === 'sentimentTrendChart') {
                updateChartData(sentimentTrendChart, chartData[period]);
            } else if (chartId === 'sentimentTrendChart2') {
                updateChartData(sentimentTrendChart2, chartData[period]);
            }
        });
    });

    // Function to update chart data
    function updateChartData(chart, data) {
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.positive;
        chart.data.datasets[1].data = data.neutral;
        chart.data.datasets[2].data = data.negative;
        chart.update();
    }

    // Initialize second sentiment trend chart for the sentiment analysis section
    const sentimentTrendCtx2 = document.getElementById('sentimentTrendChart2');
    let sentimentTrendChart2;

    if (sentimentTrendCtx2) {
        sentimentTrendChart2 = new Chart(sentimentTrendCtx2, {
            type: 'line',
            data: {
                labels: chartData.week.labels,
                datasets: [
                    {
                        label: 'Positive',
                        data: chartData.week.positive,
                        borderColor: '#4cc9a0',
                        backgroundColor: 'rgba(76, 201, 160, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Neutral',
                        data: chartData.week.neutral,
                        borderColor: '#8d99ae',
                        backgroundColor: 'rgba(141, 153, 174, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Negative',
                        data: chartData.week.negative,
                        borderColor: '#f72585',
                        backgroundColor: 'rgba(247, 37, 133, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }

    // Source Distribution Chart
    const sourceDistributionCtx = document.getElementById('sourceDistributionChart');
    if (sourceDistributionCtx) {
        const sourceDistributionChart = new Chart(sourceDistributionCtx, {
            type: 'bar',
            data: {
                labels: ['Twitter', 'Facebook', 'Instagram', 'Reddit', 'News', 'Reviews'],
                datasets: [{
                    label: 'Mentions',
                    data: [450, 320, 280, 120, 40, 24],
                    backgroundColor: [
                        '#1da1f2',
                        '#4267b2',
                        '#e1306c',
                        '#ff4500',
                        '#0077b5',
                        '#ff9800'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

/**
 * Update sentiment trend chart based on period
 */
function updateSentimentTrendChart(chart, period) {
    let labels, positiveData, neutralData, negativeData;

    switch (period) {
        case 'week':
            labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            positiveData = [65, 70, 68, 75, 80, 82, 85];
            neutralData = [25, 20, 22, 15, 12, 10, 8];
            negativeData = [10, 10, 10, 10, 8, 8, 7];
            break;
        case 'month':
            labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
            positiveData = [68, 72, 75, 80];
            neutralData = [22, 18, 15, 12];
            negativeData = [10, 10, 10, 8];
            break;
        case 'quarter':
            labels = ['Jan', 'Feb', 'Mar'];
            positiveData = [60, 70, 80];
            neutralData = [25, 20, 12];
            negativeData = [15, 10, 8];
            break;
    }

    chart.data.labels = labels;
    chart.data.datasets[0].data = positiveData;
    chart.data.datasets[1].data = neutralData;
    chart.data.datasets[2].data = negativeData;
    chart.update();
}

/**
 * Initialize word cloud
 */
function initWordCloud() {
    const wordCloudContainer = document.getElementById('wordCloud');

    if (wordCloudContainer && typeof d3 !== 'undefined' && typeof d3.layout.cloud !== 'undefined') {
        // Sample word data
        const words = [
            { text: 'quality', size: 70 },
            { text: 'excellent', size: 60 },
            { text: 'service', size: 50 },
            { text: 'product', size: 45 },
            { text: 'recommend', size: 40 },
            { text: 'great', size: 35 },
            { text: 'customer', size: 30 },
            { text: 'experience', size: 25 },
            { text: 'price', size: 20 },
            { text: 'value', size: 15 },
            { text: 'amazing', size: 35 },
            { text: 'support', size: 30 },
            { text: 'helpful', size: 25 },
            { text: 'fast', size: 20 },
            { text: 'reliable', size: 15 },
            { text: 'easy', size: 35 },
            { text: 'satisfied', size: 30 },
            { text: 'delivery', size: 25 },
            { text: 'responsive', size: 20 },
            { text: 'professional', size: 15 }
        ];

        // Set up word cloud
        const width = wordCloudContainer.offsetWidth;
        const height = 300;

        const layout = d3.layout.cloud()
            .size([width, height])
            .words(words)
            .padding(5)
            .rotate(() => ~~(Math.random() * 2) * 90)
            .font('Impact')
            .fontSize(d => d.size)
            .on('end', draw);

        layout.start();

        function draw(words) {
            d3.select('#wordCloud').append('svg')
                .attr('width', layout.size()[0])
                .attr('height', layout.size()[1])
                .append('g')
                .attr('transform', `translate(${layout.size()[0] / 2},${layout.size()[1] / 2})`)
                .selectAll('text')
                .data(words)
                .enter().append('text')
                .style('font-size', d => `${d.size}px`)
                .style('font-family', 'Impact')
                .style('fill', () => d3.schemeCategory10[Math.floor(Math.random() * 10)])
                .attr('text-anchor', 'middle')
                .attr('transform', d => `translate(${d.x},${d.y})rotate(${d.rotate})`)
                .text(d => d.text);
        }

        // Handle sentiment filter buttons
        document.querySelectorAll('.chart-card-header [data-sentiment]').forEach(button => {
            button.addEventListener('click', function() {
                // Update active button
                document.querySelectorAll('.chart-card-header [data-sentiment]').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');

                // Update word cloud based on sentiment
                const sentiment = this.getAttribute('data-sentiment');
                updateWordCloud(sentiment);
            });
        });

        function updateWordCloud(sentiment) {
            // In a real implementation, this would fetch different words based on sentiment
            // For this demo, we'll just log the sentiment
            console.log(`Updating word cloud for sentiment: ${sentiment}`);
        }
    }
}

/**
 * Initialize filters
 */
function initFilters() {
    // Source filter
    const sourceFilter = document.querySelector('#sourceFilter');
    if (sourceFilter) {
        sourceFilter.addEventListener('change', function() {
            filterMentions();
        });
    }

    // Sentiment filter
    const sentimentFilter = document.querySelector('#sentimentFilter');
    if (sentimentFilter) {
        sentimentFilter.addEventListener('change', function() {
            filterMentions();
        });
    }

    // Sort filter
    const sortFilter = document.querySelector('#sortFilter');
    if (sortFilter) {
        sortFilter.addEventListener('change', function() {
            filterMentions();
        });
    }

    // Search
    const mentionSearch = document.querySelector('#mentionSearch');
    if (mentionSearch) {
        mentionSearch.addEventListener('input', function() {
            filterMentions();
        });
    }
}

/**
 * Filter mentions based on selected filters
 */
function filterMentions() {
    const source = document.querySelector('#sourceFilter').value;
    const sentiment = document.querySelector('#sentimentFilter').value;
    const sort = document.querySelector('#sortFilter').value;
    const search = document.querySelector('#mentionSearch').value.toLowerCase();

    // In a real implementation, this would fetch filtered data from the server
    // For this demo, we'll just log the filters
    console.log('Filtering mentions:', { source, sentiment, sort, search });
}

/**
 * Initialize modals
 */
function initModals() {
    // Add brand modal
    const addBrandModal = document.querySelector('#addBrandModal');
    if (addBrandModal) {
        addBrandModal.addEventListener('hidden.bs.modal', function() {
            // Reset form
            document.querySelector('#addBrandForm').reset();
        });
    }
}

/**
 * Initialize file upload functionality
 */
function initFileUpload() {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('file');
    const uploadButton = document.getElementById('uploadButton');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('progressBar');
    const uploadStatus = document.getElementById('uploadStatus');

    if (fileInput) {
        fileInput.addEventListener('change', function() {
            // Show file name
            const fileName = this.files[0]?.name || 'No file selected';
            const fileLabel = document.querySelector('.custom-file-label');
            if (fileLabel) {
                fileLabel.textContent = fileName;
            }

            // Enable/disable upload button based on file selection
            if (uploadButton) {
                uploadButton.disabled = !this.files.length;
            }
        });
    }


    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Show progress bar
            if (uploadProgress) {
                uploadProgress.classList.remove('d-none');
            }

            // Get form data
            const formData = new FormData(this);

            // Simulate file upload with progress
            let progress = 0;
            const interval = setInterval(() => {
                progress += 10;
                if (progressBar) {
                    progressBar.style.width = `${progress}%`;
                    progressBar.setAttribute('aria-valuenow', progress);
                }

                if (progress >= 100) {
                    clearInterval(interval);

                    // Update status
                    if (uploadStatus) {
                        uploadStatus.textContent = 'Processing file...';
                    }

                    // Simulate server processing time
                    setTimeout(() => {
                        // Add to recent uploads
                        const mockResponse = {
                            file_id: 'file_' + Date.now(),
                            filename: fileInput.files[0].name,
                            timestamp: new Date().toLocaleString(),
                            total_reviews: Math.floor(Math.random() * 500) + 50,
                            sentiment_distribution: {
                                positive: Math.floor(Math.random() * 70) + 30,
                                neutral: Math.floor(Math.random() * 30) + 10,
                                negative: Math.floor(Math.random() * 20) + 5
                            }
                        };

                        addUploadToTable(mockResponse);

                        // Reset form
                        uploadForm.reset();
                        if (fileLabel) {
                            fileLabel.textContent = 'Choose file';
                        }
                        if (uploadButton) {
                            uploadButton.disabled = true;
                        }

                        // Hide progress
                        if (uploadProgress) {
                            uploadProgress.classList.add('d-none');
                        }
                        if (progressBar) {
                            progressBar.style.width = '0%';
                            progressBar.setAttribute('aria-valuenow', 0);
                        }

                        // Show success message
                        const alertContainer = document.getElementById('alertContainer');
                        if (alertContainer) {
                            const alert = document.createElement('div');
                            alert.className = 'alert alert-success alert-dismissible fade show';
                            alert.innerHTML = `
                                <strong>Success!</strong> File uploaded and processed successfully.
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            `;
                            alertContainer.appendChild(alert);

                            // Auto dismiss after 5 seconds
                            setTimeout(() => {
                                alert.classList.remove('show');
                                setTimeout(() => {
                                    alertContainer.removeChild(alert);
                                }, 150);
                            }, 5000);
                        }
                    }, 1500);
                }
            }, 200);

            // In a real implementation, this would be an AJAX request to the server
            // For this demo, we'll simulate the upload process

            // Check if file is selected
            if (!fileInput.files.length) {
                alert('Please select a file to upload');
                return;
            }

            // Show loading state
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Uploading...';

            // Send file to server
            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Reset form
                uploadForm.reset();

                // Show success message
                alert('File uploaded successfully!');

                // Update dashboard with new data
                updateDashboardWithFileData(data);

                // Add to recent uploads
                addToRecentUploads(data);

                // Reset button
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            })
            .catch(error => {
                console.error('Error uploading file:', error);
                alert('Error uploading file: ' + error.message);

                // Reset button
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnText;
            });
        });
    }
}

/**
 * Load recent uploads
 */
function loadRecentUploads() {
    const recentUploadsTable = document.getElementById('recentUploadsTable');

    if (recentUploadsTable) {
        // In a real implementation, this would fetch data from the server
        // For this demo, we'll use mock data
        const mockUploads = [
            {
                file_id: 'abc123',
                filename: 'amazon_reviews.csv',
                total_reviews: 250,
                sentiment_distribution: { positive: 150, neutral: 50, negative: 50 },
                average_score: 0.75,
                timestamp: '2023-06-15 14:30:22'
            },
            {
                file_id: 'def456',
                filename: 'customer_feedback.csv',
                total_reviews: 120,
                sentiment_distribution: { positive: 80, neutral: 30, negative: 10 },
                average_score: 0.82,
                timestamp: '2023-06-10 09:15:45'
            }
        ];

        // Clear table
        recentUploadsTable.innerHTML = '';

        // Add rows
        mockUploads.forEach(upload => {
            const row = document.createElement('tr');

            // Calculate sentiment percentages
            const total = upload.total_reviews;
            const positivePercent = Math.round((upload.sentiment_distribution.positive / total) * 100);
            const neutralPercent = Math.round((upload.sentiment_distribution.neutral / total) * 100);
            const negativePercent = Math.round((upload.sentiment_distribution.negative / total) * 100);

            row.innerHTML = `
                <td>${upload.filename}</td>
                <td>${upload.timestamp}</td>
                <td>${upload.total_reviews}</td>
                <td>
                    <div class="sentiment-mini-chart">
                        <div class="sentiment-mini-bar positive" style="width: ${positivePercent}%"></div>
                        <div class="sentiment-mini-bar neutral" style="width: ${neutralPercent}%"></div>
                        <div class="sentiment-mini-bar negative" style="width: ${negativePercent}%"></div>
                    </div>
                    <div class="sentiment-mini-text">
                        <span class="positive">${positivePercent}%</span> /
                        <span class="neutral">${neutralPercent}%</span> /
                        <span class="negative">${negativePercent}%</span>
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary view-results-btn" data-file-id="${upload.file_id}">
                        <i class="fas fa-chart-bar me-1"></i>View Results
                    </button>
                    <a href="/download/${upload.file_id}" class="btn btn-sm btn-outline-secondary">
                        <i class="fas fa-download me-1"></i>Download
                    </a>
                </td>
            `;

            recentUploadsTable.appendChild(row);
        });

        // Add event listeners to view results buttons
        document.querySelectorAll('.view-results-btn').forEach(button => {
            button.addEventListener('click', function() {
                const fileId = this.getAttribute('data-file-id');
                viewUploadResults(fileId);
            });
        });
    }
}

/**
 * Add a new upload to the recent uploads table
 */
function addToRecentUploads(data) {
    const recentUploadsTable = document.getElementById('recentUploadsTable');

    if (recentUploadsTable) {
        // Create new row
        const row = document.createElement('tr');

        // Calculate sentiment percentages
        const total = data.total_reviews;
        const positivePercent = Math.round((data.sentiment_distribution.positive / total) * 100);
        const neutralPercent = Math.round((data.sentiment_distribution.neutral / total) * 100);
        const negativePercent = Math.round((data.sentiment_distribution.negative / total) * 100);

        row.innerHTML = `
            <td>${data.filename}</td>
            <td>${data.timestamp || new Date().toLocaleString()}</td>
            <td>${data.total_reviews}</td>
            <td>
                <div class="sentiment-mini-chart">
                    <div class="sentiment-mini-bar positive" style="width: ${positivePercent}%"></div>
                    <div class="sentiment-mini-bar neutral" style="width: ${neutralPercent}%"></div>
                    <div class="sentiment-mini-bar negative" style="width: ${negativePercent}%"></div>
                </div>
                <div class="sentiment-mini-text">
                    <span class="positive">${positivePercent}%</span> /
                    <span class="neutral">${neutralPercent}%</span> /
                    <span class="negative">${negativePercent}%</span>
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-primary view-results-btn" data-file-id="${data.file_id}">
                    <i class="fas fa-chart-bar me-1"></i>View Results
                </button>
                <a href="/download/${data.file_id}" class="btn btn-sm btn-outline-secondary">
                    <i class="fas fa-download me-1"></i>Download
                </a>
            </td>
        `;

        // Add to top of table
        if (recentUploadsTable.firstChild) {
            recentUploadsTable.insertBefore(row, recentUploadsTable.firstChild);
        } else {
            recentUploadsTable.appendChild(row);
        }

        // Add event listener to view results button
        row.querySelector('.view-results-btn').addEventListener('click', function() {
            viewUploadResults(data.file_id);
        });
    }
}

/**
 * View upload results
 */
function viewUploadResults(fileId) {
    // Show the results section
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.classList.remove('active');
    });

    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        resultsSection.classList.add('active');
    }

    // Update the section title
    const sectionTitle = document.querySelector('#sectionTitle');
    if (sectionTitle) {
        sectionTitle.textContent = 'Analysis Results';
    }

    // Update the sidebar active item
    const navLinks = document.querySelectorAll('.sidebar-menu li');
    navLinks.forEach(link => {
        link.classList.remove('active');
    });

    const resultsLink = document.querySelector('.sidebar-menu li a[href="#results"]');
    if (resultsLink) {
        resultsLink.parentElement.classList.add('active');
    }

    // In a real implementation, this would fetch data from the server
    // For this demo, we'll use mock data
    let resultData;

    if (fileId === 'abc123') {
        resultData = {
            file_id: 'abc123',
            filename: 'amazon_reviews.csv',
            total_reviews: 250,
            sentiment_distribution: { positive: 150, neutral: 50, negative: 50 },
            average_score: 0.75,
            insights: {
                key_strengths: [
                    'Product quality is highly praised',
                    'Customer service is responsive',
                    'Fast shipping and delivery'
                ],
                key_weaknesses: [
                    'Some users reported packaging issues',
                    'Price is considered high by some customers'
                ],
                improvement_suggestions: [
                    'Consider improving packaging',
                    'Offer more competitive pricing or discounts'
                ],
                customer_satisfaction_summary: 'Overall customer satisfaction is high with 75% positive sentiment.'
            }
        };
    } else if (fileId === 'def456') {
        resultData = {
            file_id: 'def456',
            filename: 'customer_feedback.csv',
            total_reviews: 120,
            sentiment_distribution: { positive: 80, neutral: 30, negative: 10 },
            average_score: 0.82,
            insights: {
                key_strengths: [
                    'User interface is intuitive and easy to use',
                    'Features meet customer needs',
                    'Reliable performance'
                ],
                key_weaknesses: [
                    'Limited customization options',
                    'Some features are hard to discover'
                ],
                improvement_suggestions: [
                    'Add more customization options',
                    'Improve feature discoverability with better UI/UX',
                    'Consider adding a tutorial for new users'
                ],
                customer_satisfaction_summary: 'Customer satisfaction is very high with 82% positive sentiment.'
            }
        };
    } else {
        // For dynamically added uploads
        resultData = {
            file_id: fileId,
            filename: 'uploaded_file.csv',
            total_reviews: 180,
            sentiment_distribution: { positive: 100, neutral: 50, negative: 30 },
            average_score: 0.7,
            insights: {
                key_strengths: [
                    'Product meets customer expectations',
                    'Good value for money',
                    'Helpful customer support'
                ],
                key_weaknesses: [
                    'Some quality control issues reported',
                    'Delivery delays in some regions'
                ],
                improvement_suggestions: [
                    'Strengthen quality control processes',
                    'Improve delivery logistics',
                    'Consider expanding customer support hours'
                ],
                customer_satisfaction_summary: 'Customer satisfaction is good with 70% positive sentiment, but there is room for improvement.'
            }
        };
    }

    // Show results in modal
    const modal = new bootstrap.Modal(document.getElementById('uploadResultModal'));
    const modalContent = document.getElementById('uploadResultContent');
    const downloadBtn = document.getElementById('downloadResultsBtn');

    // Update download button
    downloadBtn.href = `/download/${fileId}`;

    // Create content
    let content = `
        <div class="result-summary">
            <h4>${resultData.filename}</h4>
            <div class="result-stats">
                <div class="stat-item">
                    <span class="stat-label">Total Reviews:</span>
                    <span class="stat-value">${resultData.total_reviews}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Average Score:</span>
                    <span class="stat-value">${resultData.average_score.toFixed(2)}</span>
                </div>
            </div>

            <div class="sentiment-distribution-chart">
                <h5>Sentiment Distribution</h5>
                <div class="sentiment-bars">
    `;

    // Calculate percentages
    const total = resultData.total_reviews;
    const positivePercent = Math.round((resultData.sentiment_distribution.positive / total) * 100);
    const neutralPercent = Math.round((resultData.sentiment_distribution.neutral / total) * 100);
    const negativePercent = Math.round((resultData.sentiment_distribution.negative / total) * 100);

    content += `
                    <div class="sentiment-bar-container">
                        <div class="sentiment-label">Positive</div>
                        <div class="sentiment-bar-wrapper">
                            <div class="sentiment-bar positive" style="width: ${positivePercent}%"></div>
                            <div class="sentiment-value">${resultData.sentiment_distribution.positive} (${positivePercent}%)</div>
                        </div>
                    </div>
                    <div class="sentiment-bar-container">
                        <div class="sentiment-label">Neutral</div>
                        <div class="sentiment-bar-wrapper">
                            <div class="sentiment-bar neutral" style="width: ${neutralPercent}%"></div>
                            <div class="sentiment-value">${resultData.sentiment_distribution.neutral} (${neutralPercent}%)</div>
                        </div>
                    </div>
                    <div class="sentiment-bar-container">
                        <div class="sentiment-label">Negative</div>
                        <div class="sentiment-bar-wrapper">
                            <div class="sentiment-bar negative" style="width: ${negativePercent}%"></div>
                            <div class="sentiment-value">${resultData.sentiment_distribution.negative} (${negativePercent}%)</div>
                        </div>
                    </div>
                </div>
            </div>
    `;

    // Add insights
    if (resultData.insights) {
        content += `
            <div class="insights-section mt-4">
                <h5>Actionable Insights</h5>

                <div class="row">
        `;

        if (resultData.insights.key_strengths && resultData.insights.key_strengths.length > 0) {
            content += `
                    <div class="col-md-6">
                        <div class="insight-card strengths">
                            <h6><i class="fas fa-star me-2"></i>Key Strengths</h6>
                            <ul>
            `;

            resultData.insights.key_strengths.forEach(strength => {
                content += `<li>${strength}</li>`;
            });

            content += `
                            </ul>
                        </div>
                    </div>
            `;
        }

        if (resultData.insights.key_weaknesses && resultData.insights.key_weaknesses.length > 0) {
            content += `
                    <div class="col-md-6">
                        <div class="insight-card weaknesses">
                            <h6><i class="fas fa-exclamation-triangle me-2"></i>Key Weaknesses</h6>
                            <ul>
            `;

            resultData.insights.key_weaknesses.forEach(weakness => {
                content += `<li>${weakness}</li>`;
            });

            content += `
                            </ul>
                        </div>
                    </div>
            `;
        }

        content += `
                </div>

                <div class="row mt-3">
        `;

        if (resultData.insights.improvement_suggestions && resultData.insights.improvement_suggestions.length > 0) {
            content += `
                    <div class="col-md-6">
                        <div class="insight-card suggestions">
                            <h6><i class="fas fa-lightbulb me-2"></i>Improvement Suggestions</h6>
                            <ul>
            `;

            resultData.insights.improvement_suggestions.forEach(suggestion => {
                content += `<li>${suggestion}</li>`;
            });

            content += `
                            </ul>
                        </div>
                    </div>
            `;
        }

        if (resultData.insights.customer_satisfaction_summary) {
            content += `
                    <div class="col-md-6">
                        <div class="insight-card summary">
                            <h6><i class="fas fa-users me-2"></i>Customer Satisfaction</h6>
                            <p>${resultData.insights.customer_satisfaction_summary}</p>
                        </div>
                    </div>
            `;
        }

        content += `
                </div>
            </div>
        `;
    }

    // Set content and show modal
    modalContent.innerHTML = content;
    modal.show();

    // Update dashboard with this data
    updateDashboardWithFileData(resultData);
}

/**
 * Update dashboard with file data
 */
function updateDashboardWithFileData(data) {
    // Update sentiment distribution chart
    const sentimentDistributionCtx = document.getElementById('sentimentDistributionChart');
    if (sentimentDistributionCtx) {
        const chartInstance = Chart.getChart(sentimentDistributionCtx);
        if (chartInstance) {
            chartInstance.data.datasets[0].data = [
                data.sentiment_distribution.positive,
                data.sentiment_distribution.neutral,
                data.sentiment_distribution.negative
            ];
            chartInstance.update();
        }
    }

    // Update stat cards
    const totalMentionsValue = document.querySelector('.stat-card:nth-child(1) .stat-value');
    if (totalMentionsValue) {
        totalMentionsValue.textContent = data.total_reviews.toLocaleString();
    }

    const sentimentScoreValue = document.querySelector('.stat-card:nth-child(2) .stat-value');
    if (sentimentScoreValue) {
        sentimentScoreValue.innerHTML = Math.round(data.average_score * 100) + '<span>/100</span>';
    }

    // Update source distribution chart to show file source
    const sourceDistributionCtx = document.getElementById('sourceDistributionChart');
    if (sourceDistributionCtx) {
        const chartInstance = Chart.getChart(sourceDistributionCtx);
        if (chartInstance) {
            chartInstance.data.labels = ['Uploaded CSV', 'Twitter', 'Facebook', 'Instagram', 'Reddit', 'News'];
            chartInstance.data.datasets[0].data = [
                data.total_reviews,
                0,
                0,
                0,
                0,
                0
            ];
            chartInstance.update();
        }
    }
}

/**
 * Update dashboard data
 */
function updateDashboardData(startDate, endDate) {
    const brand = document.querySelector('#brandSelector').value;

    // In a real implementation, this would fetch data from the server
    // For this demo, we'll just log the parameters
    console.log('Updating dashboard data:', { brand, startDate, endDate });

    // Simulate loading state
    document.querySelectorAll('.chart-card-body, .stat-card-body').forEach(element => {
        element.style.opacity = '0.5';
    });

    // Simulate data update
    setTimeout(() => {
        document.querySelectorAll('.chart-card-body, .stat-card-body').forEach(element => {
            element.style.opacity = '1';
        });
    }, 1000);
}
