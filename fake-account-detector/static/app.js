const API_BASE = '';

// Defensive: remove any residual "Posting Timeline" elements
// This ensures the section is removed even if the HTML is cached in the browser.
document.addEventListener('DOMContentLoaded', () => {
    try {
        const walkers = Array.from(document.querySelectorAll('div, h1, h2, h3, p, span'));
        for (const node of walkers) {
            if (!node || !node.textContent) continue;
            if (node.textContent.trim().toLowerCase().includes('posting timeline')) {
                // remove nearest viz-card ancestor if present, otherwise remove the node
                const card = node.closest('.viz-card') || node.closest('.visualizations') || node;
                if (card && card.parentNode) {
                    card.parentNode.removeChild(card);
                }
            }
        }
    } catch (err) {
        console.warn('Cleanup script failed', err);
    }

    // Fetch model metrics and initialize threshold slider
    (async function loadMetrics(){
        try{
            const res = await fetch('/api/metrics');
            const data = await res.json();
            if (res.ok && data.success && data.metrics){
                const m = data.metrics;
                document.getElementById('metric-accuracy').textContent = (m.accuracy || '—');
                document.getElementById('metric-precision').textContent = (m.precision || '—');
                document.getElementById('metric-recall').textContent = (m.recall || '—');
                document.getElementById('metric-f1').textContent = (m.f1 || '—');
                const modelThreshold = Number(m.decision_threshold ?? m.model_threshold ?? 0.5);
                const slider = document.getElementById('threshold-slider');
                const val = document.getElementById('threshold-value');
                if (slider){
                    slider.value = modelThreshold.toFixed(2);
                    val.textContent = Number(slider.value).toFixed(2);
                    slider.addEventListener('input', () => { val.textContent = Number(slider.value).toFixed(2); });
                }
            }
        }catch(err){
            // ignore
        }
    })();
});

document
    .getElementById('analysis-form')
    .addEventListener('submit', analyzeAccount);

document
    .getElementById('fetch-btn')
    .addEventListener('click', fetchInstagram);

document
    .getElementById('username')
    .addEventListener('input', clearErrors);

/* -------------------- CLEAR ERRORS -------------------- */

function clearErrors() {
    document
        .getElementById('fetch-error')
        .classList.add('hidden');

    document
        .getElementById('skip-section')
        .classList.add('hidden');
}

/* -------------------- FETCH INSTAGRAM -------------------- */

async function fetchInstagram() {

    const username =
        document.getElementById('username').value.trim();

    const errorBox =
        document.getElementById('fetch-error');

    const errorMessage =
        document.getElementById('error-message');

    if (!username) {
        showError('Please enter Instagram username');
        return;
    }

    if (!/^[a-zA-Z0-9_.]{1,30}$/.test(username)) {
        showError('Invalid Instagram username');
        return;
    }

    const fetchBtn =
        document.getElementById('fetch-btn');

    const loading =
        document.getElementById('loading');

    const originalText = fetchBtn.innerHTML;

    try {

        fetchBtn.disabled = true;
        fetchBtn.innerHTML = 'Fetching...';

        loading.classList.remove('hidden');

        const response = await fetch(
            `${API_BASE}/api/fetch-instagram`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username
                })
            }
        );

        const data = await response.json();

        if (!response.ok || !data.success) {

            let msg =
                data.error ||
                'Failed to fetch Instagram profile';

            if (msg.includes('Not Found')) {
                msg =
                    `@${username} not found`;
            }

            showError(msg);

            document
                .getElementById('skip-section')
                .classList.remove('hidden');

            return;
        }

        populateProfile(data.profile);

    } catch (err) {

        showError(
            'Network error. Please try again.'
        );

    } finally {

        loading.classList.add('hidden');

        fetchBtn.disabled = false;
        fetchBtn.innerHTML = originalText;
    }
}

/* -------------------- POPULATE PROFILE -------------------- */

function populateProfile(profile) {

    // persist profile for later analysis submission
    window.latestProfile = profile || {};


    document.getElementById('bio').value =
        profile.bio || '';

    document.getElementById('followers').value =
        profile.followers_count || 0;

    document.getElementById('following').value =
        profile.following_count || 0;

    document.getElementById('posts').value =
        profile.media_count || 0;

    document.getElementById('profile-pic').value =
        profile.profile_pic_url ? 1 : 0;

    const profileDiv =
        document.getElementById('fetched-profile');

    const profileData =
        document.getElementById('profile-data');

    profileData.innerHTML = `
        <div class="stats-display">

            <div class="stat-item">
                <span class="stat-label">Username</span>
                <span class="stat-value">
                    @${profile.username}
                </span>
            </div>

            <div class="stat-item">
                <span class="stat-label">Followers</span>
                <span class="stat-value">
                    ${formatNumber(profile.followers_count)}
                </span>
            </div>

            <div class="stat-item">
                <span class="stat-label">Following</span>
                <span class="stat-value">
                    ${formatNumber(profile.following_count)}
                </span>
            </div>

            <div class="stat-item">
                <span class="stat-label">Posts</span>
                <span class="stat-value">
                    ${formatNumber(profile.media_count)}
                </span>
            </div>

            <div class="stat-item">
                <span class="stat-label">Verified</span>
                <span class="stat-value">${profile.is_verified ? 'Yes' : 'No'}</span>
            </div>

            <div class="stat-item">
                <span class="stat-label">External Link</span>
                <span class="stat-value">${profile.external_url ? '<a href="' + profile.external_url + '" target="_blank">link</a>' : '—'}</span>
            </div>

        </div>
    `;

    profileDiv.classList.remove('hidden');

    setTimeout(() => {
        profileDiv.style.opacity = '1';
    }, 100);
}

/* -------------------- ANALYZE ACCOUNT -------------------- */

async function analyzeAccount(e) {

    e.preventDefault();

    const loading =
        document.getElementById('loading');

    loading.classList.remove('hidden');

    const payload = {

        username:
            document.getElementById('username').value || 'N/A',

        bio:
            document.getElementById('bio').value,

        followers_count:
            parseInt(
                document.getElementById('followers').value
            ) || 0,

        following_count:
            parseInt(
                document.getElementById('following').value
            ) || 0,

        media_count:
            parseInt(
                document.getElementById('posts').value
            ) || 0,

        has_profile_pic:
            parseInt(
                document.getElementById('profile-pic').value
            )
    };

    // include fetched profile enrichments if available
    if (window.latestProfile) {
        payload.profile = window.latestProfile;
    }

    // include user-selected threshold if available
    const slider = document.getElementById('threshold-slider');
    if (slider){
        payload.threshold = Number(slider.value);
    }

    try {

        const response = await fetch(
            `${API_BASE}/api/analyze`,
            {
                method: 'POST',

                headers: {
                    'Content-Type': 'application/json'
                },

                body: JSON.stringify(payload)
            }
        );

        const result = await response.json();

        if (!response.ok || !result.success) {

            showError(
                result.error ||
                'Analysis failed'
            );

            return;
        }

        displayResults(result);

    } catch (err) {

        showError(
            'Server error occurred'
        );

    } finally {

        loading.classList.add('hidden');
    }
}

/* -------------------- DISPLAY RESULTS -------------------- */

function displayResults(result) {

    const results =
        document.getElementById('results');

    const noResults =
        document.getElementById('no-results');

    const fakeProbability =
        Math.round(
            (Number(result.confidence) || 0) * 100
        );

    const isFake =
        result.prediction === 'Fake';

    /* PREDICTION */

    const predictionEl =
        document.getElementById('result-prediction');

    predictionEl.textContent =
        isFake ? 'FAKE' : 'REAL';

    predictionEl.className =
        `metric-value ${isFake ? 'fake' : 'real'}`;

    /* CONFIDENCE */

    document.getElementById(
        'result-confidence'
    ).textContent = `${fakeProbability}%`;

    /* RISK */

    document.getElementById(
        'result-risk-score'
    ).textContent = `${result.risk_score}/100`;

    /* VERDICT */

    document.getElementById(
        'result-verdict'
    ).textContent = result.verdict;

    document.getElementById(
        'result-verdict-detail'
    ).textContent = result.verdict;

    document.getElementById(
        'result-reasoning'
    ).textContent = result.reasoning;

    /* PROGRESS */

    const progress =
        document.getElementById('progress-fill');

    progress.style.width =
        `${fakeProbability}%`;

    document.getElementById(
        'progress-text'
    ).textContent =
        `${fakeProbability}% fake probability`;

    /* CHIP */

    const chip =
        document.getElementById('result-chip');

    chip.className = 'result-chip';

    if (result.risk_score >= 75) {

        chip.classList.add('fake');
        chip.textContent = 'HIGH RISK';

    } else if (result.risk_score >= 45) {

        chip.classList.add('suspicious');
        chip.textContent = 'SUSPICIOUS';

    } else {

        chip.classList.add('genuine');
        chip.textContent = 'SAFE';
    }

    /* INSIGHTS */

    const insights = [

        `Risk Score: ${result.risk_score}/100`,

        `Confidence Level: ${fakeProbability}%`,

        result.reasoning,

        isFake
            ? 'Profile shows suspicious activity patterns'
            : 'Profile appears authentic'
    ];

    const insightsEl =
        document.getElementById('result-insights');

    // include heuristic features returned by the API
    if (result.features) {
        for (const [k, v] of Object.entries(result.features)) {
            insights.push(`${k.replace(/_/g, ' ')}: ${Number(v).toFixed(3)}`);
        }
    }

    insightsEl.innerHTML = insights.map(item => `<li>${item}</li>`).join('');

    /* SHOW */

    results.classList.remove('hidden');
    noResults.classList.add('hidden');

    results.style.opacity = '0';

    setTimeout(() => {

        results.style.transition =
            'all .4s ease';

        results.style.opacity = '1';

    }, 100);

    setTimeout(() => {

        results.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });

    }, 300);

    // render visualizations
    try {
        renderCharts(result);
    } catch (err) {
        console.warn('Chart render failed', err);
    }
}


/* -------------------- CHARTS -------------------- */

let postsChart = null;

function renderCharts(result) {
    // Disable posts timeline chart: remove any existing chart instance
    // and remove the DOM node so the section cannot reappear.
    let postsCtx = document.getElementById('posts-timeline');
    if (postsChart) {
        try { postsChart.destroy(); } catch (e) { /* ignore */ }
        postsChart = null;
    }

    if (postsCtx) {
        const card = postsCtx.closest('.viz-card') || postsCtx.closest('.visualizations') || postsCtx.parentNode;
        if (card && card.parentNode) {
            card.parentNode.removeChild(card);
        } else if (postsCtx.parentNode) {
            postsCtx.parentNode.removeChild(postsCtx);
        }
        postsCtx = null;
    }

    const days = 30;
    const labels = Array.from({length: days}, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (days - 1 - i));
        return d.toISOString().slice(0,10);
    });

    // POSTS TIMELINE DATA
    let postsData = new Array(days).fill(0);

    const profile = window.latestProfile || {};

    if (profile.posts && profile.posts.length) {
        // count posts per day based on timestamps
        profile.posts.forEach(p => {
            const ts = p.timestamp || p.created_at || p.time || null;
            if (!ts) return;
            const d = new Date(ts);
            if (isNaN(d)) return;
            const iso = d.toISOString().slice(0,10);
            const idx = labels.indexOf(iso);
            if (idx >= 0) postsData[idx]++;
        });
    } else if (result.features && result.features.avg_posts_per_day) {
        const lambda = Math.max(0.01, Number(result.features.avg_posts_per_day));
        for (let i=0;i<days;i++){
            // Poisson-like sampling via Math.random
            const val = Math.round(lambda + (Math.random()-0.5)*lambda);
            postsData[i] = Math.max(0, val);
        }
    } else {
        // fallback using media_count
        const avg = Math.max(0, (profile.media_count || 0) / 365.0);
        for (let i=0;i<days;i++) postsData[i] = Math.round(avg + (Math.random()-0.5)*avg);
    }

    if (postsCtx && postsCtx.getContext) {
        if (postsChart) postsChart.destroy();
        postsChart = new Chart(postsCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Posts',
                    data: postsData,
                    borderColor: '#00d4aa',
                    backgroundColor: 'rgba(0,212,170,0.12)',
                    fill: true,
                    tension: 0.3,
                }]
            },
            options: {
                maintainAspectRatio: false,
                scales: { x: { display: false }, y: { beginAtZero: true, display: true } },
                plugins: { legend: { display: false } }
            }
        });
    }

}

/* -------------------- HELPERS -------------------- */

function showError(message) {

    const errorBox =
        document.getElementById('fetch-error');

    const errorMessage =
        document.getElementById('error-message');

    errorMessage.textContent = message;

    errorBox.classList.remove('hidden');
}

function skipToManual() {

    document
        .getElementById('fetch-error')
        .classList.add('hidden');

    document
        .getElementById('skip-section')
        .classList.add('hidden');

    document
        .getElementById('analysis-form')
        .scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
}

function formatNumber(num) {

    if (num >= 1000000) {
        return (
            (num / 1000000).toFixed(1) + 'M'
        );
    }

    if (num >= 1000) {
        return (
            (num / 1000).toFixed(1) + 'K'
        );
    }

    return num.toString();
}