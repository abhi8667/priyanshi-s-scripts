document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initClock();
    loadDashboard();
    setupEventListeners();
});

function initClock() {
    const clockEl = document.getElementById('live-clock');
    if (!clockEl) return;
    const update = () => {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const dateStr = now.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });
        clockEl.innerText = `${timeStr} · ${dateStr} · Stratified Optimization`;
    };
    update();
    setInterval(update, 10000);
}

// Toast Manager
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✨' : type === 'error' ? '❌' : '⚡';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Global Tab Switcher Function
function switchTab(tabId) {
    const modePills = document.querySelectorAll('.mode-pill');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const stepItems = document.querySelectorAll('.step-item');
    const navMenu = document.getElementById('nav-pills-menu');
    const hamIcon = document.getElementById('hamburger-icon');

    // Close mobile menu
    if (navMenu) navMenu.classList.remove('open');
    if (hamIcon) {
        hamIcon.className = 'fa-solid fa-bars';
    }

    modePills.forEach(b => b.classList.remove('active'));
    tabPanes.forEach(pane => pane.classList.remove('active'));
    stepItems.forEach(item => item.classList.remove('active'));

    // Highlight target mode pill
    const targetModePill = document.querySelector(`.mode-pill[data-tab="${tabId}"]`);
    if (targetModePill) targetModePill.classList.add('active');

    // Highlight target step item
    const targetStepItem = document.querySelector(`.step-item[data-tab="${tabId}"]`);
    if (targetStepItem) targetStepItem.classList.add('active');

    const targetPane = document.getElementById(tabId);
    if (targetPane) {
        targetPane.classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });

        if (tabId === 'dashboard') loadDashboard();
        if (tabId === 'students') loadStudents();
        if (tabId === 'backups') loadBackups();
    }

    // Update Mobile Thumb Zone Action Bar
    updateThumbZoneBar(tabId);
}

// Mobile Thumb Zone Action Bar Updater
function updateThumbZoneBar(tabId) {
    const bar = document.getElementById('thumb-zone-bar');
    const btn = document.getElementById('thumb-action-btn');
    const label = document.getElementById('thumb-btn-label');
    const icon = document.getElementById('thumb-btn-icon');
    if (!bar || !btn || !label) return;

    if (tabId === 'import') {
        label.innerText = 'Step 1: Choose Excel File';
        icon.className = 'fa-solid fa-cloud-arrow-up';
        btn.className = 'btn btn-amber';
        btn.onclick = () => document.getElementById('excel-file-input')?.click();
    } else if (tabId === 'groups') {
        label.innerText = 'Step 2: Run Stratification';
        icon.className = 'fa-solid fa-bolt';
        btn.className = 'btn btn-amber';
        btn.onclick = () => runGroupAllocation();
    } else if (tabId === 'group-a-venues') {
        label.innerText = 'Step 3: Allocate Group A';
        icon.className = 'fa-solid fa-bolt';
        btn.className = 'btn btn-amber';
        btn.onclick = () => runGroupAVenueAllocation();
    } else if (tabId === 'group-b-venues') {
        label.innerText = 'Step 4: Allocate Group B';
        icon.className = 'fa-solid fa-bolt';
        btn.className = 'btn btn-sage';
        btn.onclick = () => runGroupBVenueAllocation();
    } else if (tabId === 'exports') {
        label.innerText = 'Step 5: Download Master Excel';
        icon.className = 'fa-solid fa-file-excel';
        btn.className = 'btn btn-amber';
        btn.onclick = () => window.location.href = '/api/export/excel?group=Master';
    } else {
        label.innerText = 'Go to Dashboard';
        icon.className = 'fa-solid fa-chart-pie';
        btn.className = 'btn btn-raised';
        btn.onclick = () => switchTab('dashboard');
    }
}

// Navigation & Hamburger Controller
function initNavigation() {
    const modePills = document.querySelectorAll('.mode-pill');
    const stepItems = document.querySelectorAll('.step-item');
    const hamBtn = document.getElementById('hamburger-toggle');
    const navMenu = document.getElementById('nav-pills-menu');
    const hamIcon = document.getElementById('hamburger-icon');

    if (hamBtn && navMenu) {
        hamBtn.addEventListener('click', () => {
            const isOpen = navMenu.classList.toggle('open');
            if (hamIcon) {
                hamIcon.className = isOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars';
            }
        });
    }

    modePills.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    stepItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    // Initial thumb bar setup
    updateThumbZoneBar('dashboard');
}

// 0. Dashboard View
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

        // Render Branch-Wise Cumulative Distribution
        const deptList = document.getElementById('dept-dist-list');
        if (deptList) {
            deptList.innerHTML = '';
            const deptDist = data.department_distribution || {};
            const deptEntries = Object.entries(deptDist);
            if (deptEntries.length === 0) {
                deptList.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem;">No student data uploaded yet.</p>';
            } else {
                for (const [dept, count] of deptEntries) {
                    const percent = Math.round((count / total) * 100);
                    deptList.innerHTML += `
                        <div style="margin-bottom:14px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:0.9rem; font-weight:600;">
                                <span><i class="fa-solid fa-code-branch text-[#7FB069] mr-1"></i> ${dept}</span>
                                <span style="color:var(--accent-sage); font-weight:700;">${count} (${percent}%)</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${percent}%; background:var(--accent-sage);"></div>
                            </div>
                        </div>`;
                }
            }
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

// 1. Import View
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

    const runGABtn = document.getElementById('run-ga-venue-btn');
    if (runGABtn) runGABtn.addEventListener('click', runGroupAVenueAllocation);

    const runGBBtn = document.getElementById('run-gb-venue-btn');
    if (runGBBtn) runGBBtn.addEventListener('click', runGroupBVenueAllocation);

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
        statusEl.innerHTML = `<span style="color:var(--accent-emerald)">✨ File analyzed: <strong>${data.file_name}</strong></span>`;
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
                ✅ Import Complete! Total: ${result.imported_count} Records | New: ${result.new_count} | Updated: ${result.updated_count}
            </div>`;
        showToast(`Imported ${result.imported_count} records`, 'success');
        loadDashboard();
        setTimeout(() => switchTab('groups'), 1200);
    } else {
        commitMsg.innerHTML = `
            <div style="padding:14px; background:rgba(244, 63, 94, 0.15); border:1px solid rgba(244,63,94,0.3); border-radius:10px; color:var(--accent-rose); font-weight:600;">
                ❌ ${result.errors.join('<br>')}
            </div>`;
        showToast("Import validation failed", 'error');
    }
}

// 2. Step 2: Group Allocation
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
                    <p style="font-size:1.05rem; margin-top:4px;">Group A: <strong>${result.group_a_count}</strong> | Group B: <strong>${result.group_b_count}</strong></p>
                </div>`;
            showToast("Group A and Group B created!", 'success');
            loadDashboard();
        }
    } catch (err) {
        statusEl.innerHTML = `<span style="color:var(--accent-rose)">Allocation failed.</span>`;
        showToast("Allocation failed", 'error');
    }
}

// Dynamic Slot & Venue Builders
function addDynamicSlot(prefix) {
    const container = document.getElementById(`${prefix}-slots-container`);
    if (!container) return;
    const count = container.querySelectorAll(`.${prefix}-slot-row`).length + 1;
    const div = document.createElement('div');
    div.className = `form-group ${prefix}-slot-row flex items-center gap-2 mb-3`;
    div.innerHTML = `
        <input type="text" class="form-control ${prefix}-slot-input" placeholder="Event ${count} Name (e.g. Lab Visit / Workshop)">
        <button onclick="this.parentElement.remove()" class="btn btn-raised" style="padding:6px 10px; font-size:0.75rem; color:var(--accent-rose);" title="Remove">✕</button>
    `;
    container.appendChild(div);
}

function addDynamicVenue(prefix) {
    const container = document.getElementById(`${prefix}-venues-container`);
    if (!container) return;
    const count = container.querySelectorAll(`.${prefix}-venue-row`).length + 1;
    const div = document.createElement('div');
    div.className = `form-group ${prefix}-venue-row flex items-center gap-2 mb-3`;
    div.innerHTML = `
        <input type="text" class="form-control ${prefix}-venue-name" placeholder="Venue ${count} Name">
        <input type="number" class="form-control ${prefix}-venue-cap" placeholder="Seats" style="max-width:110px;">
        <button onclick="this.parentElement.remove()" class="btn btn-raised" style="padding:6px 10px; font-size:0.75rem; color:var(--accent-rose);" title="Remove">✕</button>
    `;
    container.appendChild(div);
}

// 3. Step 3: Group A Venue Allocation
async function runGroupAVenueAllocation() {
    const statusEl = document.getElementById('ga-venue-status');
    statusEl.innerHTML = '<span style="color:var(--accent-cyan); font-weight:600;">🚀 Executing Branch-Mixing Solver for Group A...</span>';

    // Collect all dynamic slots for Group A
    const slots = [];
    document.querySelectorAll('#ga-slots-container .ga-slot-input').forEach(input => {
        const val = input.value.trim();
        if (val) slots.push({ slot_name: val, start_time: '09:30 AM', end_time: '11:30 AM' });
    });

    // Collect all dynamic venues for Group A
    const venues = [];
    document.querySelectorAll('#ga-venues-container .ga-venue-row').forEach(row => {
        const name = row.querySelector('.ga-venue-name')?.value?.trim();
        const cap = parseInt(row.querySelector('.ga-venue-cap')?.value || '0');
        if (name && cap > 0) venues.push({ name: name, capacity: cap });
    });

    try {
        const res = await fetch('/api/venues/allocate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_group: 'Group A',
                slots: slots,
                venues: venues
            })
        });
        const result = await res.json();

        if (result.success) {
            statusEl.innerHTML = `
                <div style="padding:20px; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16,185,129,0.3); border-radius:14px; color:var(--accent-emerald);">
                    <h3 style="margin-bottom:6px;">🏛️ Group A Venue Optimization Completed!</h3>
                    <p style="font-size:1.05rem; margin-top:4px;">Allocated <strong>${result.allocated_count}</strong> Group A students across ${venues.length} venues and ${slots.length} time slots with equal branch mixing.</p>
                </div>`;
            showToast("Group A venues allocated!", 'success');
        }
    } catch (err) {
        statusEl.innerHTML = `<span style="color:var(--accent-rose)">Group A allocation failed.</span>`;
        showToast("Group A allocation failed", 'error');
    }
}

async function clearAllStudentData() {
    if (!confirm("Are you sure you want to delete ALL uploaded student data and clear allocations? This action will reset your database so you can start completely fresh.")) {
        return;
    }
    
    try {
        if (typeof showToast === 'function') showToast("Clearing all student data...", "info");
        const res = await fetch('/api/data/reset', { method: 'POST' });
        const data = await res.json();
        
        if (data.success) {
            if (typeof showToast === 'function') showToast("All student data successfully cleared!", "success");
            const mappingWrapper = document.getElementById('mapping-wrapper');
            if (mappingWrapper) mappingWrapper.style.display = 'none';
            const uploadStatus = document.getElementById('upload-status');
            if (uploadStatus) uploadStatus.innerHTML = '<span style="color:var(--accent-sage);">Database cleared successfully. Ready for fresh import.</span>';
            loadDashboard();
        } else {
            alert(data.detail || "Failed to clear student data.");
        }
    } catch (err) {
        alert("Error connecting to server: " + err.message);
    }
}

// 4. Step 4: Group B Venue Allocation
async function runGroupBVenueAllocation() {
    const statusEl = document.getElementById('gb-venue-status');
    statusEl.innerHTML = '<span style="color:var(--accent-cyan); font-weight:600;">🚀 Executing Branch-Mixing Solver for Group B...</span>';

    // Collect all dynamic slots for Group B
    const slots = [];
    document.querySelectorAll('#gb-slots-container .gb-slot-input').forEach(input => {
        const val = input.value.trim();
        if (val) slots.push({ slot_name: val, start_time: '09:30 AM', end_time: '11:30 AM' });
    });

    // Collect all dynamic venues for Group B
    const venues = [];
    document.querySelectorAll('#gb-venues-container .gb-venue-row').forEach(row => {
        const name = row.querySelector('.gb-venue-name')?.value?.trim();
        const cap = parseInt(row.querySelector('.gb-venue-cap')?.value || '0');
        if (name && cap > 0) venues.push({ name: name, capacity: cap });
    });

    try {
        const res = await fetch('/api/venues/allocate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_group: 'Group B',
                slots: slots,
                venues: venues
            })
        });
        const result = await res.json();

        if (result.success) {
            statusEl.innerHTML = `
                <div style="padding:20px; background:rgba(16, 185, 129, 0.15); border:1px solid rgba(16,185,129,0.3); border-radius:14px; color:var(--accent-emerald);">
                    <h3 style="margin-bottom:6px;">🏛️ Group B Venue Optimization Completed!</h3>
                    <p style="font-size:1.05rem; margin-top:4px;">Allocated <strong>${result.allocated_count}</strong> Group B students across ${venues.length} venues and ${slots.length} time slots with equal branch mixing.</p>
                </div>`;
            showToast("Group B venues allocated!", 'success');
        }
    } catch (err) {
        statusEl.innerHTML = `<span style="color:var(--accent-rose)">Group B allocation failed.</span>`;
        showToast("Group B allocation failed", 'error');
    }
}

// Student Database View
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

// Venue Manager View
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

// Backup & Rollback View
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

// Audit Logs View
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
