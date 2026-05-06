/* ─────────────────────────────────────────────────────────────────────────────
   LinkedIn Job Scraper Dashboard - JavaScript
   ───────────────────────────────────────────────────────────────────────────── */

const API_BASE = '/api';

// ─── State Management ────────────────────────────────────────────────────────
const state = {
    currentTab: 'jobs',
    currentResumeId: null,
    jobs: [],
    bookmarks: [],
    resumeInfo: null,
    filters: {
        location: '',
        workType: '',
        search: ''
    }
};

// ─── Tab Navigation ─────────────────────────────────────────────────────────
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', (e) => {
        const tabName = e.target.dataset.tab;
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    state.currentTab = tabName;

    // Load data for specific tabs
    if (tabName === 'jobs') {
        loadJobs();
    } else if (tabName === 'bookmarks') {
        loadBookmarks();
    } else if (tabName === 'scraper') {
        loadScraperStatus();
    } else if (tabName === 'resume') {
        loadResumeInfo();
        loadAllResumes();
    }
}

// ─── Jobs Management ────────────────────────────────────────────────────────
async function loadJobs() {
    const container = document.getElementById('jobs-container');
    const loading = document.getElementById('jobs-loading');
    
    try {
        loading.style.display = 'block';
        container.innerHTML = '';

        const params = new URLSearchParams({
            skip: 0,
            limit: 50,
            ...(state.filters.location && { location: state.filters.location }),
            ...(state.filters.workType && { work_type: state.filters.workType }),
            ...(state.filters.search && { search: state.filters.search })
        });

        const response = await fetch(`${API_BASE}/jobs?${params}`);
        if (!response.ok) throw new Error('Failed to load jobs');
        
        const jobs = await response.json();
        state.jobs = jobs;

        if (jobs.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>📭 No jobs found. Try changing your filters or trigger the scraper.</p></div>';
            return;
        }

        jobs.forEach(job => renderJobCard(job));
    } catch (error) {
        console.error('Error loading jobs:', error);
        container.innerHTML = `<div class="empty-state"><p>❌ Error loading jobs: ${error.message}</p></div>`;
    } finally {
        loading.style.display = 'none';
    }
}

function renderJobCard(job) {
    const container = document.getElementById('jobs-container');
    
    const relevanceScore = job.relevance_score || 0;
    const scoreBadgeClass = relevanceScore >= 70 ? 'high' : relevanceScore >= 40 ? 'medium' : 'low';
    
    const card = document.createElement('div');
    card.className = 'job-card';
    card.innerHTML = `
        <div class="job-card-header">
            <div>
                <h3 class="job-card-title">${escapeHtml(job.title)}</h3>
                <p class="job-card-company">${escapeHtml(job.company_name || job.company_id || 'Unknown Company')}</p>
                <div class="job-card-location">📍 ${escapeHtml(job.location || 'Location not specified')}</div>
            </div>
            <div>
                ${job.relevance_score !== null ? `<div class="relevance-badge ${scoreBadgeClass}">${relevanceScore.toFixed(0)}%</div>` : ''}
            </div>
        </div>
        
        <div class="job-card-details">
            ${job.formatted_work_type ? `<div class="job-card-detail"><span class="job-card-detail-label">Type:</span><span class="job-card-detail-value">${escapeHtml(job.formatted_work_type)}</span></div>` : ''}
            ${job.min_salary ? `<div class="job-card-detail"><span class="job-card-detail-label">Salary:</span><span class="job-card-detail-value">$${job.min_salary.toLocaleString()} - $${job.max_salary?.toLocaleString()}</span></div>` : ''}
            ${job.formatted_experience_level ? `<div class="job-card-detail"><span class="job-card-detail-label">Level:</span><span class="job-card-detail-value">${escapeHtml(job.formatted_experience_level)}</span></div>` : ''}
        </div>

        <div class="job-card-actions">
            <button class="bookmark-btn ${job.is_bookmarked ? 'bookmarked' : ''}" onclick="toggleBookmark('${escapeHtml(job.job_id)}')">
                ${job.is_bookmarked ? '⭐ Saved' : '☆ Save'}
            </button>
            <button class="btn btn-primary" onclick="showJobDetails('${escapeHtml(job.job_id)}')">
                View Details
            </button>
        </div>
    `;

    container.appendChild(card);
}

async function showJobDetails(jobId) {
    try {
        const response = await fetch(`${API_BASE}/jobs/${jobId}`);
        if (!response.ok) throw new Error('Failed to load job details');
        
        const job = await response.json();
        
        const modal = document.getElementById('job-modal');
        const modalBody = document.getElementById('modal-body');
        
        modalBody.innerHTML = `
            <div>
                <h2>${escapeHtml(job.title)}</h2>
                <p class="text-gray">${escapeHtml(job.company_name || job.company_id || 'Unknown Company')} • ${escapeHtml(job.location)}</p>
                
                ${job.relevance_score !== null ? `<div style="margin: 1rem 0"><span class="relevance-badge">${job.relevance_score.toFixed(0)}%</span></div>` : ''}
                
                <h3>Details</h3>
                <p><strong>Work Type:</strong> ${escapeHtml(job.formatted_work_type || 'N/A')}</p>
                <p><strong>Experience Level:</strong> ${escapeHtml(job.formatted_experience_level || 'N/A')}</p>
                <p><strong>Remote:</strong> ${job.remote_allowed ? 'Yes' : 'No'}</p>
                ${job.min_salary ? `<p><strong>Salary:</strong> $${job.min_salary.toLocaleString()} - $${job.max_salary?.toLocaleString()}</p>` : ''}
                
                <h3 style="margin-top: 1.5rem">Description</h3>
                <p>${escapeHtml(job.description || 'No description available').substring(0, 1000)}...</p>
                
                ${job.skills_desc ? `<div style="margin-top: 1.5rem"><h3>Required Skills</h3><p>${escapeHtml(job.skills_desc)}</p></div>` : ''}
                
                <div style="margin-top: 2rem">
                    <a href="${job.job_posting_url}" target="_blank" class="btn btn-primary">
                        View on LinkedIn
                    </a>
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
    } catch (error) {
        alert(`Error loading job details: ${error.message}`);
    }
}

async function toggleBookmark(jobId) {
    try {
        const isBookmarked = await isJobBookmarked(jobId);
        
        if (isBookmarked) {
            const response = await fetch(`${API_BASE}/jobs/bookmark/${jobId}`, { method: 'DELETE' });
        } else {
            const response = await fetch(`${API_BASE}/jobs/bookmark/${jobId}`, { method: 'POST' });
        }
        
        // Reload jobs to update UI
        loadJobs();
    } catch (error) {
        console.error('Error toggling bookmark:', error);
    }
}

async function isJobBookmarked(jobId) {
    const response = await fetch(`${API_BASE}/jobs`);
    const jobs = await response.json();
    const job = jobs.find(j => j.job_id === jobId);
    return job?.is_bookmarked || false;
}

// Filter buttons
document.getElementById('apply-filters').addEventListener('click', () => {
    state.filters.search = document.getElementById('search-input').value;
    state.filters.location = document.getElementById('location-filter').value;
    state.filters.workType = document.getElementById('work-type-filter').value;
    loadJobs();
});

document.getElementById('clear-filters').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    document.getElementById('location-filter').value = '';
    document.getElementById('work-type-filter').value = '';
    state.filters = { location: '', workType: '', search: '' };
    loadJobs();
});

document.getElementById('load-relevant-jobs').addEventListener('click', () => {
    openResumeSelectionModal();
});

async function openResumeSelectionModal() {
    const modal = document.getElementById('resume-modal');
    const listContainer = document.getElementById('resume-list');
    modal.classList.remove('hidden');
    
    try {
        const response = await fetch(`${API_BASE}/resume/all`);
        const resumes = await response.json();
        
        if (resumes.length === 0) {
            listContainer.innerHTML = '<p class="text-gray">No resumes found. Please upload one first.</p>';
            return;
        }
        
        listContainer.innerHTML = resumes.map(r => `
            <div class="resume-card" style="border: 1px solid var(--border); padding: 1rem; margin-bottom: 0.5rem; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${escapeHtml(r.filename)}</strong><br/>
                    <span class="text-sm text-gray">${new Date(r.uploaded_at).toLocaleString()}</span>
                </div>
                <button class="btn btn-primary" onclick="loadRelevantJobs('${r.resume_id}')">Select</button>
            </div>
        `).join('');
    } catch (err) {
        listContainer.innerHTML = `<p class="text-gray">Failed to load resumes: ${err.message}</p>`;
    }
}

document.getElementById('resume-modal-close').addEventListener('click', () => {
    document.getElementById('resume-modal').classList.add('hidden');
});

async function loadRelevantJobs(resume_id) {
    document.getElementById('resume-modal').classList.add('hidden');
    
    const container = document.getElementById('jobs-container');
    const loading = document.getElementById('jobs-loading');
    
    try {
        loading.style.display = 'block';
        container.innerHTML = '';

        const params = new URLSearchParams({
            resume_id: resume_id,
            skip: 0,
            limit: 50
        });

        const response = await fetch(`${API_BASE}/jobs/relevant?${params}`);
        if (!response.ok) {
            if (response.status === 404) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>No relevance scores found for this resume yet.</p>
                        <button class="btn btn-primary" onclick="analyzeAndLoad('${resume_id}')">Analyze Now</button>
                    </div>
                `;
                return;
            }
            const errData = await response.json().catch(() => null);
            throw new Error(errData?.detail || 'Failed to load relevant jobs');
        }
        
        const jobs = await response.json();
        state.jobs = jobs;

        if (jobs.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>📭 No relevant jobs found.</p></div>';
            return;
        }

        jobs.forEach(job => renderJobCard(job));
    } catch (error) {
        console.error('Error loading relevant jobs:', error);
        container.innerHTML = `<div class="empty-state"><p>❌ Error loading relevant jobs: ${error.message}</p></div>`;
    } finally {
        loading.style.display = 'none';
    }
}

async function analyzeAndLoad(resume_id) {
    const container = document.getElementById('jobs-container');
    container.innerHTML = '<div class="loading">Analyzing resume against all jobs... This may take a few seconds.</div>';
    
    try {
        const response = await fetch(`${API_BASE}/resume/analyze-relevance?resume_id=${resume_id}`, { method: 'POST' });
        if (!response.ok) throw new Error('Analysis failed');
        
        // After successful analysis, load the relevant jobs!
        await loadRelevantJobs(resume_id);
    } catch (err) {
        container.innerHTML = `<div class="empty-state"><p>❌ Error analyzing resume: ${err.message}</p></div>`;
    }
}

// ─── Resume Management ──────────────────────────────────────────────────────
const uploadArea = document.getElementById('upload-area');
const resumeFile = document.getElementById('resume-file');

uploadArea.addEventListener('click', () => resumeFile.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.background = '#f0f0f0';
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.background = 'white';
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.background = 'white';
    resumeFile.files = e.dataTransfer.files;
    uploadResume();
});

document.getElementById('upload-resume').addEventListener('click', uploadResume);

async function uploadResume() {
    const file = resumeFile.files[0];
    if (!file) {
        alert('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/resume/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');
        
        const data = await response.json();
        state.currentResumeId = data.resume_id;
        
        loadResumeInfo();
        alert('✅ Resume uploaded successfully!');
    } catch (error) {
        alert(`❌ Error uploading resume: ${error.message}`);
    }
}

async function loadResumeInfo() {
    try {
        const response = await fetch(`${API_BASE}/resume/latest`);
        if (!response.ok) {
            document.getElementById('resume-info').classList.add('hidden');
            return;
        }

        const resume = await response.json();
        state.currentResumeId = resume.resume_id;
        state.resumeInfo = resume;

        document.getElementById('resume-filename').textContent = resume.filename;
        document.getElementById('resume-date').textContent = new Date(resume.uploaded_at).toLocaleDateString();

        const skillsList = document.getElementById('skills-list');
        if (resume.extracted_skills && resume.extracted_skills.length > 0) {
            skillsList.innerHTML = resume.extracted_skills
                .map(skill => `<span class="skill-tag">${escapeHtml(skill)}</span>`)
                .join('');
        } else {
            skillsList.innerHTML = '<span class="text-gray">No specific skills extracted</span>';
        }

        document.getElementById('resume-info').classList.remove('hidden');
    } catch (error) {
        document.getElementById('resume-info').classList.add('hidden');
    }
}

async function loadAllResumes() {
    const listContainer = document.getElementById('past-resumes-list');
    try {
        const response = await fetch(`${API_BASE}/resume/all`);
        if (!response.ok) throw new Error('Failed to load past resumes');
        const resumes = await response.json();
        
        if (resumes.length === 0) {
            listContainer.innerHTML = '<p class="text-gray">No past resumes found.</p>';
            return;
        }
        
        listContainer.innerHTML = resumes.map(r => `
            <div style="border-bottom: 1px solid var(--border); padding: 0.5rem 0; display: flex; justify-content: space-between;">
                <div>
                    <strong>${escapeHtml(r.filename)}</strong>
                    <div class="text-sm text-gray">Uploaded: ${new Date(r.uploaded_at).toLocaleString()}</div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        listContainer.innerHTML = `<p class="text-gray">${err.message}</p>`;
    }
}

document.getElementById('analyze-resume').addEventListener('click', analyzeResume);

async function analyzeResume() {
    if (!state.currentResumeId) {
        alert('Please upload a resume first');
        return;
    }

    try {
        const btn = document.getElementById('analyze-resume');
        btn.disabled = true;
        btn.textContent = 'Analyzing...';

        const response = await fetch(`${API_BASE}/resume/analyze-relevance?resume_id=${state.currentResumeId}`, { method: 'POST' });
        if (!response.ok) throw new Error('Analysis failed');

        const results = await response.json();

        document.getElementById('jobs-analyzed').textContent = results.total_jobs_analyzed;
        document.getElementById('avg-score').textContent = `${results.average_relevance_score.toFixed(1)}%`;
        document.getElementById('high-matches').textContent = results.high_matches;

        document.getElementById('analysis-results').classList.remove('hidden');
        
        // Switch to jobs tab to see results
        setTimeout(() => switchTab('jobs'), 1000);
    } catch (error) {
        alert(`Error analyzing resume: ${error.message}`);
    } finally {
        const btn = document.getElementById('analyze-resume');
        btn.disabled = false;
        btn.textContent = 'Analyze & Calculate Relevance Scores';
    }
}

// ─── Bookmarks ──────────────────────────────────────────────────────────────
async function loadBookmarks() {
    const container = document.getElementById('bookmarks-container');
    const noBookmarks = document.getElementById('no-bookmarks');

    try {
        const response = await fetch(`${API_BASE}/jobs/bookmarks/all`);
        if (!response.ok) throw new Error('Failed to load bookmarks');

        const bookmarks = await response.json();
        state.bookmarks = bookmarks;

        if (bookmarks.length === 0) {
            container.innerHTML = '';
            noBookmarks.style.display = 'block';
            return;
        }

        noBookmarks.style.display = 'none';
        container.innerHTML = '';

        bookmarks.forEach(bookmark => {
            const card = document.createElement('div');
            card.className = 'job-card';
            card.innerHTML = `
                <h3 class="job-card-title">${escapeHtml(bookmark.job_title)}</h3>
                <p class="job-card-company">${escapeHtml(bookmark.company || 'Unknown')}</p>
                ${bookmark.relevance_score !== null ? `<div style="margin: 1rem 0"><span class="relevance-badge">${bookmark.relevance_score.toFixed(0)}%</span></div>` : ''}
                ${bookmark.notes ? `<p><strong>Notes:</strong> ${escapeHtml(bookmark.notes)}</p>` : ''}
                <small class="text-gray">Saved: ${new Date(bookmark.created_at).toLocaleDateString()}</small>
                <div class="job-card-actions">
                    <button class="btn btn-danger" onclick="removeBookmark('${bookmark.bookmark_id}')">Remove</button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading bookmarks:', error);
        container.innerHTML = `<div class="empty-state"><p>❌ Error loading bookmarks</p></div>`;
    }
}

async function removeBookmark(bookmarkId) {
    try {
        const response = await fetch(`${API_BASE}/jobs/bookmark/${bookmarkId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to remove bookmark');
        
        loadBookmarks();
    } catch (error) {
        alert(`Error removing bookmark: ${error.message}`);
    }
}

// ─── Scraper Control ────────────────────────────────────────────────────────
async function loadScraperStatus() {
    try {
        const response = await fetch(`${API_BASE}/scraper/status`);
        if (!response.ok) throw new Error('Failed to load status');

        const status = await response.json();

        document.getElementById('scraper-status').textContent = status.is_running ? 'Running 🔄' : 'Idle ✓';
        document.getElementById('total-jobs').textContent = status.jobs_scraped_total;
        document.getElementById('jobs-detailed').textContent = status.jobs_with_details;
        document.getElementById('pending-jobs').textContent = status.pending_jobs;

        document.getElementById('start-scraper').disabled = status.is_running;
        document.getElementById('stop-scraper').disabled = !status.is_running;
    } catch (error) {
        console.error('Error loading scraper status:', error);
    }
}

document.getElementById('start-scraper').addEventListener('click', async () => {
    const fetchDetails = document.getElementById('fetch-details').checked;

    try {
        const response = await fetch(`${API_BASE}/scraper/trigger`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_details: fetchDetails })
        });

        if (!response.ok) throw new Error('Failed to start scraper');

        alert('✅ Scraper started!');
        loadScraperStatus();
    } catch (error) {
        alert(`Error starting scraper: ${error.message}`);
    }
});

document.getElementById('stop-scraper').addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_BASE}/scraper/stop`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to stop scraper');

        alert('✅ Scraper stopped!');
        loadScraperStatus();
    } catch (error) {
        alert(`Error stopping scraper: ${error.message}`);
    }
});

document.getElementById('refresh-status').addEventListener('click', loadScraperStatus);

// ─── Modal ──────────────────────────────────────────────────────────────────
document.getElementById('job-modal').addEventListener('click', (e) => {
    if (e.target.id === 'job-modal' || e.target.className === 'modal-close') {
        document.getElementById('job-modal').classList.add('hidden');
    }
});

// ─── Utilities ──────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ─── Initialize ─────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    loadJobs();
    loadResumeInfo();
    loadScraperStatus();
});

// Auto-refresh scraper status
setInterval(loadScraperStatus, 5000);
