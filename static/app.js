document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadDashboard();
    setupEventListeners();
});

// Toast Manager
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : '⚡';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Navigation Controller
function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            navBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));

            btn.classList.add('active');
            const targetPane = document.getElementById(targetTab);
            if (targetPane) {
                targetPane.classList.add('active');
                
                // Auto load data based on active tab
                if (targetTab === 'dashboard') loadDashboard();
                if (targetTab === 'students') loadStudents();
                if (targetTab === 'venues') loadVenues();
                if (targetTab === 'backups') loadBackups();
                if (targetTab === 'logs') loadLogs();
            }
        });
    });
}

// 1. Dashboard View
async function loadDashboard() {
    try {
        const res = await fetch('/api/dashboard');
        const data = await res.json();

        document.getElementById('stat-total-students').innerText = data.total_students || 0;
        document.getElementById('stat-allocated-groups').innerText = data.allocated_groups || 0;
        document.getElementById('stat-allocated-venues').innerText = data.allocated_venues || 0;
        document.getElementById('stat-pending').innerText = data.pending_allocation || 0;

        // Render Group Breakdown
        const groupList = document.getElementById('group-dist-list');
        groupList.innerHTML = '';
        const total = data.total_students || 1;
        for (const [group, count] of Object.entries(data.group_distribution || {})) {
            const percent = Math.round((count / total) * 100);
            groupList.innerHTML += `
                <div style="margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.9rem; font-weight:600;">
                        <span>${group}</span>
                        <span style="color:var(--accent-cyan);">${count} (${percent}%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${percent}%"></div>
                    </div>
                </div>`;
        }

        // Render Recent Imports
        const importsTbody = document.getElementById('recent-imports-tbody');
        importsTbody.innerHTML = '';
        (data.recent_imports || []).forEach(imp => {
            importsTbody.innerHTML += `
                <tr>
                    <td>#${imp.id}</td>
                    <td><strong>${imp.file_name}</strong></td>
                    <td><span class="badge badge-success">${imp.record_count} Records</span></td>
                    <td style="color:var(--text-muted); font-size:0.8rem;">${imp.imported_at}</td>
                </tr>`;
        });
    } catch (err) {
        console.error("Dashboard load failed:", err);
    }
}

// 2. Import Excel View
let currentImportCacheId = null;

function setupEventListeners() {
    const fileInput = document.getElementById('excel-file-input');
    const dropZone = document.getElementById('file-drop-zone');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileUpload);
    }

    const commitBtn = document.getElementById('commit-import-btn');
    if (commitBtn) commitBtn.addEventListener('click', commitImport);

    const runGroupBtn = document.getElementById('run-group-btn');
    if (runGroupBtn) runGroupBtn.addEventListener('click', runGroupAllocation);

    const runVenueBtn = document.getElementById('run-venue-btn');
    if (runVenueBtn) runVenueBtn.addEventListener('click', runVenueAllocation);

    const addVenueForm = document.getElementById('add-venue-form');
    if (addVenueForm) addVenueForm.addEventListener('submit', addVenue);

    const addSlotForm = document.getElementById('add-slot-form');
    if (addSlotForm) addSlotForm.addEventListener('submit', addSlot);

    const createBackupBtn = document.getElementById('create-backup-btn');
    if (createBackupBtn) createBackupBtn.addEventListener('click', createBackup);
}

async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const statusEl = document.getElementById('upload-status');
    statusEl.innerHTML = '<span style="color:var(--accent-cyan); font-weight:600;">⏳ Analyzing column headers with RapidFuzz...</span>';

    try {
        const res = await fetch('/api/import/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (!res.ok) {
            statusEl.innerHTML = `<span style="color:var(--accent-rose)">${data.detail}</span>`;
            showToast(data.detail, 'error');
            return;
        }

        currentImportCacheId = data.cache_id;
        statusEl.innerHTML = `<span style="color:var(--accent-emerald)">✨ File uploaded: <strong>${data.file_name}</strong></span>`;
        showToast(`Analyzed ${data.file_name} successfully`, 'success');

        renderHeaderMapper(data.raw_headers, data.suggested_mappings, data.canonical_fields);
    } catch (err) {
        statusEl.innerHTML = `<span style="color:var(--accent-rose)">Upload failed. Try again.</span>`;
        showToast("Upload failed", 'error');
    }
}

function renderHeaderMapper(rawHeaders, suggestions, canonicalFields) {
    const container = document.getElementById('mapping-container');
    const wrapper = document.getElementById('mapping-wrapper');
    wrapper.style.display = 'block';
    container.innerHTML = '';

    rawHeaders.forEach(header => {
        const mapped = suggestions[header] || '';
        let optionsHtml = `<option value="">-- Ignore Column --</option>`;
        
        canonicalFields.forEach(field => {
            const selected = field === mapped ? 'selected' : '';
            optionsHtml += `<option value="${field}" ${selected}>${field}</option>`;
        });

        container.innerHTML += `
            <div class="glass-panel" style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:10px; padding:12px 16px; align-items:center; border-radius:10px;">
                <div style="font-weight:600; font-size:0.9rem;">${header}</div>
                <select class="form-select mapper-select" data-raw="${header}">
                    ${optionsHtml}
                </select>
            </div>`;
    });
}

async function commitImport() {
    if (!currentImportCacheId) return;

    const selects = document.querySelectorAll('.mapper-select');
    const mappings = {};
    selects.forEach(s => {
        const raw = s.getAttribute('data-raw');
        const target = s.value;
        if (target) mappings[raw] = target;
    });

    const res = await fetch('/api/import/commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cache_id: currentImportCacheId, mappings: mappings })
    });
    const result = await res.json();

    const commitMsg = document.getElementById('commit-message');
    if (result.success) {
        commitMsg.innerHTML = `
            <div style="padding:14px; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16,185,129,0.3); border-radius:10px; color:var(--accent-emerald); font-weight:600;">
                ✅ Import Complete! Total: ${result.imported_count} | New: ${result.new_count} | Updated: ${result.updated_count}
            </div>`;
        showToast(`Successfully imported ${result.imported_count} records`, 'success');
        loadDashboard();
    } else {
        commitMsg.innerHTML = `
            <div style="padding:14px; background:rgba(244, 63, 94, 0.15); border:1px solid rgba(244,63,94,0.3); border-radius:10px; color:var(--accent-rose); font-weight:600;">
                ❌ ${result.errors.join('<br>')}
            </div>`;
        showToast("Import failed with validation errors", 'error');
    }
}

// 3. Student Database View
async function loadStudents() {
    const search = document.getElementById('student-search-input')?.value || '';
    const group = document.getElementById('student-group-filter')?.value || '';

    let url = `/api/students?limit=50`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (group) url += `&group_name=${encodeURIComponent(group)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();

        const tbody = document.getElementById('students-tbody');
        tbody.innerHTML = '';

        data.students.forEach(s => {
            const groupBadge = s.group_name === 'Group A' ? 'badge-a' : s.group_name === 'Group B' ? 'badge-b' : 'badge-secondary';
            tbody.innerHTML += `
                <tr>
                    <td><strong>${s.usn}</strong></td>
                    <td>${s.full_name}</td>
                    <td>${s.department}</td>
                    <td><span class="badge ${groupBadge}">${s.group_name}</span></td>
                    <td>${s.venue}</td>
                    <td>${s.time_slot}</td>
                </tr>`;
        });

        document.getElementById('students-count-lbl').innerText = `Showing ${data.students.length} of ${data.total} records`;
    } catch (err) {
        console.error("Student load error:", err);
    }
}

// 4. Group Allocation View
async function runGroupAllocation() {
    const statusEl = document.getElementById('group-alloc-status');
    statusEl.innerHTML = '<span style="color:var(--accent-cyan); font-weight:600;">⚡ Computing SHA-256 Stratified Split...</span>';

    try {
        const res = await fetch('/api/group/allocate', { method: 'POST' });
        const result = await res.json();

        if (result.success) {
            statusEl.innerHTML = `
                <div style="padding:20px; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16,185,129,0.3); border-radius:14px; color:var(--accent-emerald);">
                    <h3 style="margin-bottom:6px;">🎉 Group Stratification Completed!</h3>
                    <p style="font-size:1rem; margin-top:4px;">Group A: <strong>${result.group_a_count}</strong> | Group B: <strong>${result.group_b_count}</strong></p>
                    <p style="font-size:0.8rem; opacity:0.8; margin-top:6px;">Execution Time: ${result.execution_time_seconds.toFixed(2)}s</p>
                </div>`;
            showToast("Group Stratification complete!", 'success');
            loadDashboard();
        }
    } catch (err) {
        statusEl.innerHTML = `<span style="color:var(--accent-rose)">Allocation failed.</span>`;
        showToast("Allocation failed", 'error');
    }
}

// 5. Venue Allocation View
async function loadVenues() {
    try {
        const res = await fetch('/api/venues');
        const data = await res.json();

        const vGrid = document.getElementById('venues-grid');
        vGrid.innerHTML = '';
        data.venues.forEach(v => {
            const pct = Math.min(100, Math.round((v.filled / (v.capacity || 1)) * 100));
            vGrid.innerHTML += `
                <div class="glass-panel" style="padding:18px; border-radius:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:1.1rem; color:var(--text-primary);">${v.name}</strong>
                        <button onclick="deleteVenue(${v.id})" class="btn btn-danger" style="padding:4px 10px; font-size:0.75rem;">Delete</button>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-top:12px;">
                        <span style="color:var(--text-secondary);">Capacity: ${v.capacity}</span>
                        <span style="color:var(--accent-cyan); font-weight:700;">${v.filled} Filled</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${pct}%"></div>
                    </div>
                </div>`;
        });

        const sGrid = document.getElementById('slots-grid');
        sGrid.innerHTML = '';
        data.slots.forEach(s => {
            sGrid.innerHTML += `
                <div class="glass-panel" style="padding:14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong style="font-size:0.95rem;">${s.slot_name}</strong>
                        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">${s.start_time} - ${s.end_time}</div>
                    </div>
                    <button onclick="deleteSlot(${s.id})" class="btn btn-danger" style="padding:4px 8px; font-size:0.75rem;">Delete</button>
                </div>`;
        });
    } catch (err) {
        console.error("Venues load error:", err);
    }
}

async function addVenue(e) {
    e.preventDefault();
    const name = document.getElementById('venue-name-input').value;
    const capacity = parseInt(document.getElementById('venue-cap-input').value);

    await fetch('/api/venues/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, capacity })
    });
    document.getElementById('add-venue-form').reset();
    showToast(`Added venue '${name}'`, 'success');
    loadVenues();
}

async function deleteVenue(id) {
    if (confirm("Delete this venue?")) {
        await fetch(`/api/venues/${id}`, { method: 'DELETE' });
        showToast("Venue deleted", 'info');
        loadVenues();
    }
}

async function addSlot(e) {
    e.preventDefault();
    const slot_name = document.getElementById('slot-name-input').value;
    const start_time = document.getElementById('slot-start-input').value;
    const end_time = document.getElementById('slot-end-input').value;

    await fetch('/api/slots/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_name, start_time, end_time })
    });
    document.getElementById('add-slot-form').reset();
    showToast(`Added time slot '${slot_name}'`, 'success');
    loadVenues();
}

async function deleteSlot(id) {
    if (confirm("Delete this time slot?")) {
        await fetch(`/api/slots/${id}`, { method: 'DELETE' });
        showToast("Time slot deleted", 'info');
        loadVenues();
    }
}

async function runVenueAllocation() {
    const statusEl = document.getElementById('venue-alloc-status');
    statusEl.innerHTML = '<span style="color:var(--accent-cyan); font-weight:600;">🚀 Executing PuLP MILP Solver...</span>';

    try {
        const res = await fetch('/api/venues/allocate', { method: 'POST' });
        const result = await res.json();

        if (result.success) {
            statusEl.innerHTML = `
                <div style="padding:20px; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16,185,129,0.3); border-radius:14px; color:var(--accent-emerald);">
                    <h3 style="margin-bottom:6px;">🏛️ Venue Optimization Completed!</h3>
                    <p style="font-size:1rem; margin-top:4px;">Allocated Students: <strong>${result.allocated_count}</strong> | Solver: <strong>${result.solver_name}</strong></p>
                    <p style="font-size:0.8rem; opacity:0.8; margin-top:6px;">Execution Time: ${result.execution_time_seconds.toFixed(2)}s</p>
                </div>`;
            showToast("Venue allocation complete!", 'success');
            loadVenues();
        }
    } catch (err) {
        statusEl.innerHTML = `<span style="color:var(--accent-rose)">Venue allocation failed.</span>`;
        showToast("Venue allocation failed", 'error');
    }
}

// 6. Backup & Rollback View
async function loadBackups() {
    try {
        const res = await fetch('/api/backups');
        const data = await res.json();

        const tbody = document.getElementById('backups-tbody');
        tbody.innerHTML = '';

        data.backups.forEach(b => {
            tbody.innerHTML += `
                <tr>
                    <td><strong>${b.filename}</strong></td>
                    <td style="color:var(--text-muted); font-size:0.85rem;">${b.created_at}</td>
                    <td>${(b.size_bytes / 1024).toFixed(1)} KB</td>
                    <td>
                        <button onclick="restoreBackup(${b.id})" class="btn btn-secondary" style="padding:6px 12px; font-size:0.8rem;">1-Click Rollback</button>
                    </td>
                </tr>`;
        });
    } catch (err) {
        console.error("Backup load error:", err);
    }
}

async function createBackup() {
    const formData = new FormData();
    formData.append('description', 'Manual Web Snapshot');
    await fetch('/api/backups/create', { method: 'POST', body: formData });
    showToast("Created SQLite backup snapshot", 'success');
    loadBackups();
}

async function restoreBackup(id) {
    if (confirm("Rollback database state to this snapshot? Safety backup will be saved first.")) {
        const res = await fetch('/api/backups/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ backup_id: id })
        });
        const result = await res.json();
        showToast(result.message || "Database restored", 'success');
        loadDashboard();
        loadBackups();
    }
}

// 7. Audit Logs View
async function loadLogs() {
    try {
        const res = await fetch('/api/logs');
        const logs = await res.json();

        const tbody = document.getElementById('logs-tbody');
        tbody.innerHTML = '';

        logs.forEach(l => {
            tbody.innerHTML += `
                <tr>
                    <td style="color:var(--text-muted); font-size:0.8rem;">${l.timestamp}</td>
                    <td><span class="badge badge-a">${l.action}</span></td>
                    <td style="font-size:0.85rem;">${l.entity_type || ''} #${l.entity_id || ''}</td>
                    <td style="font-size:0.85rem;">${l.details}</td>
                </tr>`;
        });
    } catch (err) {
        console.error("Logs load error:", err);
    }
}
