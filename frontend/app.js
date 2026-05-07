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
        location: [],
        workType: [],
        company: [],
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

        const params = new URLSearchParams();
        params.append('skip', 0);
        params.append('limit', 50);
        
        if (state.filters.location && state.filters.location.length) {
            state.filters.location.forEach(l => params.append('location', l));
        }
        if (state.filters.workType && state.filters.workType.length) {
            state.filters.workType.forEach(w => params.append('work_type', w));
        }
        if (state.filters.company && state.filters.company.length) {
            state.filters.company.forEach(c => params.append('company', c));
        }
        if (state.filters.search) {
            params.append('search', state.filters.search);
        }

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
            ${job.min_salary ? `<div class="job-card-detail"><span class="job-card-detail-label">Salary:</span><span class="job-card-detail-value">₹${job.min_salary.toLocaleString('en-IN')} - ₹${job.max_salary?.toLocaleString('en-IN')}</span></div>` : ''}
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
        let job = state.jobs.find(j => j.job_id === jobId);
        
        if (!job) {
            const response = await fetch(`${API_BASE}/jobs/${jobId}`);
            if (!response.ok) throw new Error('Failed to load job details');
            job = await response.json();
        }
        
        const modal = document.getElementById('job-modal');
        const modalBody = document.getElementById('modal-body');
        
        modalBody.innerHTML = `
            <div>
                <h2>${escapeHtml(job.title)}</h2>
                <p class="text-gray">${escapeHtml(job.company_name || job.company_id || 'Unknown Company')} • ${escapeHtml(job.location)}</p>
                
                ${job.relevance_score !== null ? `
                    <div style="margin-top: 1.5rem; padding: 1rem; border: 1px solid var(--border); border-radius: 8px; background: #f8fafc;">
                        <h3 style="margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.5rem;">Evaluation Results</h3>
                        
                        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                            <span class="relevance-badge ${job.relevance_score >= 70 ? 'high' : job.relevance_score >= 40 ? 'medium' : 'low'}">${job.relevance_score.toFixed(0)}%</span>
                        </div>

                        ${job.pros && job.pros.length > 0 ? `
                            <div style="margin-top: 1rem;">
                                <h4 style="color: #059669; margin-bottom: 0.5rem;">Why you are a good fit ✅</h4>
                                <ul style="color: #059669; padding-left: 1.5rem; margin-bottom: 1rem;">
                                    ${job.pros.map(p => `<li>${escapeHtml(p)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}

                        ${job.cons && job.cons.length > 0 ? `
                            <div style="margin-top: 1rem;">
                                <h4 style="color: #DC2626; margin-bottom: 0.5rem;">Areas for improvement / Missing ❌</h4>
                                <ul style="color: #DC2626; padding-left: 1.5rem; margin-bottom: 1rem;">
                                    ${job.cons.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        
                        ${job.matching_skills && job.matching_skills.length > 0 ? `
                            <div style="margin-top: 1rem;">
                                <h4 style="margin-bottom: 0.5rem;">Matching Skills Found</h4>
                                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                                    ${job.matching_skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${job.missing_skills && job.missing_skills.length > 0 ? `
                            <div style="margin-top: 1rem;">
                                <h4 style="margin-bottom: 0.5rem; color: #DC2626;">Missing Skills</h4>
                                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                                    ${job.missing_skills.map(s => `<span class="skill-tag" style="background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;">${escapeHtml(s)}</span>`).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                
                <h3 style="margin-top: 1.5rem">Details</h3>
                <p><strong>Work Type:</strong> ${escapeHtml(job.formatted_work_type || 'N/A')}</p>
                <p><strong>Experience Level:</strong> ${escapeHtml(job.formatted_experience_level || 'N/A')}</p>
                <p><strong>Remote:</strong> ${job.remote_allowed ? 'Yes' : 'No'}</p>
                ${job.min_salary ? `<p><strong>Salary:</strong> ₹${job.min_salary.toLocaleString('en-IN')} - ₹${job.max_salary?.toLocaleString('en-IN')}</p>` : ''}
                
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

function getSelectedValues(selectId) {
    const select = document.getElementById(selectId);
    return Array.from(select.selectedOptions).map(opt => opt.value).filter(v => v !== '');
}

// Filter buttons
document.getElementById('apply-filters').addEventListener('click', () => {
    state.filters.search = document.getElementById('search-input').value;
    state.filters.location = getSelectedValues('location-filter');
    state.filters.workType = getSelectedValues('work-type-filter');
    state.filters.company = getSelectedValues('company-filter');
    loadJobs();
});

document.getElementById('clear-filters').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    document.getElementById('location-filter').value = '';
    document.getElementById('work-type-filter').value = '';
    document.getElementById('company-filter').value = '';
    state.filters = { location: [], workType: [], company: [], search: '' };
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
                <button class="btn btn-secondary" onclick="selectPastResume('${r.resume_id}')" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;">Select</button>
            </div>
        `).join('');
    } catch (err) {
        listContainer.innerHTML = `<p class="text-gray">${err.message}</p>`;
    }
}

async function selectPastResume(resumeId) {
    try {
        const response = await fetch(`${API_BASE}/resume/${resumeId}`);
        if (!response.ok) throw new Error('Failed to load resume');
        
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
        
        // Scroll to top or show an indication
        document.getElementById('resume-info').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert('Error selecting resume: ' + err.message);
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

// ─── Custom Job Evaluation ──────────────────────────────────────────────────
document.getElementById('btn-eval-custom').addEventListener('click', evaluateCustomJob);

async function evaluateCustomJob() {
    if (!state.currentResumeId) {
        alert('Please upload or select a resume first.');
        return;
    }

    const jdText = document.getElementById('custom-jd-input').value.trim();
    if (!jdText) {
        alert('Please paste a job description.');
        return;
    }

    try {
        const btn = document.getElementById('btn-eval-custom');
        btn.disabled = true;
        btn.textContent = 'Evaluating...';

        const response = await fetch(`${API_BASE}/resume/evaluate-custom-job`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                resume_id: state.currentResumeId,
                job_description: jdText
            })
        });

        if (!response.ok) throw new Error('Evaluation failed');

        const results = await response.json();

        document.getElementById('custom-eval-score').textContent = `${results.score.toFixed(0)}%`;
        
        // Pros
        const prosList = document.getElementById('custom-eval-pros');
        prosList.innerHTML = results.pros && results.pros.length > 0 
            ? results.pros.map(p => `<li>${escapeHtml(p)}</li>`).join('')
            : '<li>No specific pros found.</li>';
            
        // Cons
        const consList = document.getElementById('custom-eval-cons');
        consList.innerHTML = results.cons && results.cons.length > 0
            ? results.cons.map(c => `<li>${escapeHtml(c)}</li>`).join('')
            : '<li>No missing requirements found!</li>';
            
        // Matching Skills
        const skillsContainer = document.getElementById('custom-eval-matching-skills');
        skillsContainer.innerHTML = results.matching_skills && results.matching_skills.length > 0
            ? results.matching_skills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join('')
            : '<span class="text-gray">No matching skills</span>';

        document.getElementById('custom-eval-results').classList.remove('hidden');

    } catch (error) {
        alert(`Error evaluating job: ${error.message}`);
    } finally {
        const btn = document.getElementById('btn-eval-custom');
        btn.disabled = false;
        btn.textContent = 'Evaluate Custom JD';
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
async function loadFilters() {
    try {
        const response = await fetch(`${API_BASE}/jobs/filters`);
        if (!response.ok) return;
        const filters = await response.json();
        
        const locSelect = document.getElementById('location-filter');
        locSelect.innerHTML = '<option value="">All Locations</option>' + filters.locations.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('');
        
        const typeSelect = document.getElementById('work-type-filter');
        typeSelect.innerHTML = '<option value="">All Work Types</option>' + filters.work_types.map(w => `<option value="${escapeHtml(w)}">${escapeHtml(w)}</option>`).join('');
        
        const compSelect = document.getElementById('company-filter');
        compSelect.innerHTML = '<option value="">All Companies</option>' + filters.companies.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`).join('');
    } catch (error) {
        console.error('Error loading filters', error);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    loadFilters();
    loadJobs();
    loadResumeInfo();
    loadScraperStatus();
});


