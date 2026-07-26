let jobs = [];
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const safe = (value="") => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const toast = (message) => { const el=$("#toast"); el.textContent=message; el.classList.add("show"); setTimeout(()=>el.classList.remove("show"),2200); };
const discoverableJobs = () => jobs.filter(job => ["Review", "Tailoring"].includes(job.status));

async function loadJobs() {
  try { jobs = await fetch("/api/jobs").then(r => r.json()); }
  catch { jobs = []; }
  renderJobs(discoverableJobs());
  renderPipeline();
  renderDocuments();
  $("#discoverCount").textContent = discoverableJobs().length;
  $("#applicationCount").textContent = jobs.filter(job => ["Applied","Interview","Offer","Rejected"].includes(job.status)).length;
  loadAnalytics();
}

function renderJobs(items) {
  $("#jobList").innerHTML = items.map((job, i) => `
    <article class="job-row" data-id="${job.id}" style="--i:${i}">
      <div class="score" style="--score:${job.score}"><b>${job.score}</b></div>
      <div class="job-main"><h3>${safe(job.title)}</h3><p>${safe(job.company)} · ${safe(job.location)}<span class="source-pill">${safe(job.source)}</span></p></div>
      <div class="skills">${job.skills.slice(0,3).map(skill=>`<span>${safe(skill)}</span>`).join("")}</div>
      <div class="job-meta"><strong>${safe(job.salary)}</strong><small>${job.discovered === new Date().toISOString().slice(0,10) ? "Today" : "Recently"}</small></div>
      <div class="chevron">›</div>
    </article>`).join("");
  $$(".job-row").forEach(row => row.onclick = () => openJob(row.dataset.id));
}

async function openJob(id) {
  const job = jobs.find(item => item.id === id);
  const docs = await fetch(`/api/jobs/${id}/documents`).then(r => r.json());
  const reasons = job.skills.slice(0,4).map(s => `<div class="reason"><i>✓</i> Your profile matches ${safe(s)}</div>`).join("");
  $("#dialogContent").innerHTML = `<div class="dialog-inner">
    <div class="dialog-top"><div class="company-mark">${safe(job.company.slice(0,1))}</div><div><strong>${safe(job.company)}</strong><small style="display:block;color:#777">${safe(job.source)}</small></div></div>
    <h2>${safe(job.title)}</h2><p>${safe(job.location)} · ${safe(job.salary)}</p>
    <div class="match-line"><span>${job.score}% match</span><span>${safe(job.work_type)}</span><span>${safe(job.status)}</span></div>
    <div class="dialog-section"><h3>Why this is a strong match</h3>${reasons}</div>
    <div class="dialog-section"><h3>Tailored application</h3><div class="doc-tabs"><button class="active" data-doc="resume_summary">Resume</button><button data-doc="cover_letter">Cover letter</button><button data-doc="answers">Screening answers</button></div><textarea class="doc-copy" aria-label="Editable tailored document">${safe(docs.resume_summary)}</textarea><div class="doc-tools"><button class="save-doc">Save edits</button><a class="download-doc" href="/api/jobs/${job.id}/documents/resume.txt">Download .txt</a></div></div>
  </div><div class="dialog-actions"><button class="dismiss">Dismiss</button><button class="track">Update status</button><a class="apply external" href="${safe(job.url)}" target="_blank" rel="noopener">Open application ↗</a></div>
  <div class="dismiss-panel hidden"><h3>Why isn’t this role a match?</h3><p>Your choice can prevent similar jobs from appearing in future searches.</p><select id="dismissReason"><option value="location">Location</option><option value="company">Company</option><option value="title">Role title</option><option value="keyword">Keyword</option><option value="other">Other — don’t create a rule</option></select><input id="dismissDetail" placeholder="Keyword or optional note"><div><button class="cancel-dismiss">Cancel</button><button class="confirm-dismiss">Dismiss job</button></div></div>`;
  const dialog = $("#jobDialog"); dialog.showModal();
  let activeDoc = "resume_summary";
  $$(".doc-tabs button").forEach(btn => btn.onclick = () => {
    $$(".doc-tabs button").forEach(b=>b.classList.remove("active")); btn.classList.add("active");
    activeDoc = btn.dataset.doc;
    const value = docs[btn.dataset.doc];
    $(".doc-copy").value = Array.isArray(value) ? value.map(x=>`${x.question}\n${x.answer}`).join("\n\n") : value;
    $(".download-doc").style.display = activeDoc === "answers" ? "none" : "inline-flex";
    $(".download-doc").href = `/api/jobs/${job.id}/documents/${activeDoc === "resume_summary" ? "resume" : "cover-letter"}.txt`;
  });
  $(".save-doc").onclick = async () => {
    if (activeDoc === "answers") return toast("Screening answers are copied individually during the application");
    docs[activeDoc] = $(".doc-copy").value;
    await fetch(`/api/jobs/${id}/documents`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({[activeDoc]:docs[activeDoc]})});
    toast("Document edits saved");
  };
  $(".track").onclick = async () => {
    const next = job.status === "Applied" ? "Interview" : "Applied";
    const updated = await fetch(`/api/jobs/${id}`, {method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status:next})}).then(r=>r.json());
    Object.assign(job, updated);
    dialog.close();
    renderJobs(discoverableJobs());
    renderPipeline();
    renderDocuments();
    $("#discoverCount").textContent = discoverableJobs().length;
    $("#applicationCount").textContent = jobs.filter(item => ["Applied","Interview","Offer","Rejected"].includes(item.status)).length;
    loadAnalytics();
    toast(next === "Applied" ? "Application tracked · removed from Discover" : "Interview recorded");
  };
  $(".dismiss").onclick = () => $(".dismiss-panel").classList.remove("hidden");
  $(".cancel-dismiss").onclick = () => $(".dismiss-panel").classList.add("hidden");
  $("#dismissReason").onchange = event => {
    $("#dismissDetail").placeholder = event.target.value === "keyword" ? "Required keyword to exclude" : "Optional note";
  };
  $(".confirm-dismiss").onclick = async () => {
    const reason = $("#dismissReason").value;
    const detail = $("#dismissDetail").value.trim();
    if (reason === "keyword" && !detail) return toast("Enter a keyword to exclude");
    const result = await fetch(`/api/jobs/${id}/dismiss`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({reason,detail})}).then(r=>r.json());
    Object.assign(job, result.job);
    dialog.close();
    renderJobs(discoverableJobs());
    renderPipeline();
    renderDocuments();
    $("#discoverCount").textContent = discoverableJobs().length;
    toast(result.rule ? `Dismissed · future ${reason} matches excluded` : "Job dismissed");
  };
}

function renderPipeline() {
  const groups = {Review:[],Tailoring:[],Applied:[],Interview:[]};
  jobs.forEach(j => { if (groups[j.status]) groups[j.status].push(j); });
  $("#pipeline").innerHTML = Object.entries(groups).map(([name,items])=>`<div class="lane"><h3>${name} · ${items.length}</h3>${items.map(j=>`<div class="pipeline-job" data-id="${j.id}"><strong>${safe(j.company)}</strong><small>${safe(j.title)}</small>${j.follow_up?`<em>Follow up ${safe(j.follow_up)}</em>`:""}</div>`).join("")}</div>`).join("");
  $$(".pipeline-job").forEach(row => row.onclick = () => openJob(row.dataset.id));
}

function renderDocuments() {
  $("#documentLibrary").innerHTML = jobs.filter(j=>j.status!=="Dismissed").slice(0,12).map(j=>`<div class="document-row"><strong>${safe(j.company)} · ${safe(j.title)}</strong><span>Resume + cover letter</span><span>${safe(j.status)}</span><button data-id="${j.id}">Open</button></div>`).join("");
  $$(".document-row button").forEach(btn=>btn.onclick=()=>openJob(btn.dataset.id));
}

$$(".nav-item").forEach(btn => btn.onclick = () => {
  $$(".nav-item").forEach(b=>b.classList.remove("active")); btn.classList.add("active");
  $$(".workspace").forEach(view=>view.classList.add("hidden")); $(`#${btn.dataset.view}View`).classList.remove("hidden");
  const profileName = $("#profileName").textContent === "Set up profile" ? "" : $("#profileName").textContent.split(" ")[0];
  const titles={discover:[profileName ? `Good morning, ${profileName}.` : "Your job search workspace","Your search results are scored against your saved profile."],applications:["Application pipeline","Keep every application moving."],documents:["Tailored documents","Your role-specific application library."],analytics:["Search performance","See what turns applications into interviews."],profile:["Search profile","Control how jobs are scored and documents are tailored."]};
  $("#pageTitle").textContent=titles[btn.dataset.view][0]; $("#subtitle").textContent=titles[btn.dataset.view][1];
});
$(".close").onclick=()=>$("#jobDialog").close();
$("#jobDialog").onclick=e=>{if(e.target===$("#jobDialog"))$("#jobDialog").close()};
$("#searchNow").onclick=async()=>{const btn=$("#searchNow");btn.disabled=true;btn.textContent="↻ Searching 5 boards…";try{const result=await fetch("/api/sync",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sources:["Greenhouse","Lever","Ashby","SmartRecruiters","Workday"]})}).then(r=>r.json());toast(`${result.scanned} jobs scanned · ${result.added} new matches`);await loadJobs()}catch{toast("Sync failed — check your internet connection")}finally{btn.disabled=false;btn.textContent="↻ Search now"}};
$$(".filters button:not(.tune)").forEach(btn=>btn.onclick=()=>{ $$(".filters button").forEach(b=>b.classList.remove("active"));btn.classList.add("active");const key=btn.textContent;const available=discoverableJobs();const preferred=($('[name="locations"]').value||"").toLowerCase().split(",").map(x=>x.trim()).filter(Boolean);renderJobs(key==="Remote"?available.filter(j=>j.location.toLowerCase().includes("remote")):key==="Preferred"?available.filter(j=>preferred.some(place=>j.location.toLowerCase().includes(place))):key.includes("90")?available.filter(j=>j.score>=90):available)});

async function loadProfile() {
  const profile = await fetch("/api/profile").then(r=>r.json());
  Object.entries(profile).forEach(([key,value])=>{const field=$(`[name="${key}"]`);if(field)field.value=value});
  $("#profileName").textContent = profile.name || "Set up profile";
  $("#profileLocation").textContent = profile.location || "Local workspace";
  $("#profileAvatar").textContent = profile.name ? profile.name.split(/\s+/).map(part=>part[0]).join("").slice(0,2).toUpperCase() : "?";
  if (profile.name) $("#pageTitle").textContent = `Good morning, ${profile.name.split(/\s+/)[0]}.`;
}
$("#profileForm").onsubmit=async event=>{
  event.preventDefault(); const payload=Object.fromEntries(new FormData(event.currentTarget));
  await fetch("/api/profile",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  $("#profileStatus").textContent="Saved just now. New jobs will use this profile.";toast("Search profile saved");
};

async function loadAnalytics(){
  const data=await fetch("/api/analytics").then(r=>r.json());
  const ready=jobs.filter(j=>["Review","Tailoring"].includes(j.status)).length;
  const due=jobs.filter(j=>j.follow_up&&j.follow_up<=new Date().toISOString().slice(0,10)&&j.status==="Applied").length;
  const responseRate=data.applied?Math.round(100*data.responses/data.applied):0;
  $("#metricDiscovered").textContent=data.discovered;$("#metricReady").textContent=ready;$("#metricFollowups").textContent=due;$("#metricResponse").textContent=`${responseRate}%`;
  const stages=[["Applications",data.applied],["Responses",data.responses],["Interviews",data.interviews]];
  $("#funnel").innerHTML=stages.map(([label,count],i)=>{const pct=data.applied?Math.round(count/data.applied*100):0;return `<span style="--w:${i===0?100:Math.max(20,pct)}%">${label}: ${count} <b>${pct}%</b></span>`}).join("");
  const sourceEntries=Object.entries(data.by_source);
  $("#sourceChart").innerHTML="<h3>Response rate by source</h3>"+(sourceEntries.length?sourceEntries.map(([source,v])=>{const rate=v.applications?Math.round(v.responses/v.applications*100):0;return `<div><span>${safe(source)}</span><i style="--w:${rate}%"></i><b>${rate}%</b></div>`}).join(""):"<p>No tracked applications yet.</p>");
}
loadProfile();
loadJobs();
