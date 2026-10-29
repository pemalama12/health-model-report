"use strict";
const $ = id => document.getElementById(id);
const state = {csv: "", name: "", synthetic: true, result: null, seq: 0, timer: null};
const esc = text => String(text).replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const number = value => value == null ? "N/A" : value.toFixed(3);
const percent = value => value == null ? "N/A" : `${(100 * value).toFixed(1)}%`;
const interval = (value, pct = false) => value ? `${pct ? percent(value[0]) : number(value[0])}–${pct ? percent(value[1]) : number(value[1])}` : "Interval unavailable";

function calibrationChart(points) {
  const x = n => 58 + n * 422, y = n => 230 - n * 200;
  let svg = '<svg viewBox="0 0 520 280" role="img" aria-label="Calibration: mean predicted risk versus observed outcome rate, with 95 percent confidence intervals">';
  for (let i = 0; i <= 4; i++) {
    const t = i / 4;
    svg += `<path d="M58 ${y(t)}H480" stroke="#eef1eb"/><text x="43" y="${y(t)+3}" text-anchor="end" font-size="9" fill="#95a18e">${t.toFixed(2)}</text><text x="${x(t)}" y="248" text-anchor="middle" font-size="9" fill="#95a18e">${t.toFixed(2)}</text>`;
  }
  svg += '<path d="M58 230L480 30" stroke="#b3bea7" stroke-dasharray="5 6"/><text x="270" y="273" text-anchor="middle" font-size="10" fill="#7e907c">Mean predicted probability</text><text transform="translate(13 135) rotate(-90)" text-anchor="middle" font-size="10" fill="#7e907c">Observed outcome rate</text>';
  svg += `<polyline points="${points.map(p=>`${x(p.predicted)},${y(p.observed)}`).join(" ")}" fill="none" stroke="#288978" stroke-width="2.3"/>`;
  points.forEach(p => {
    const px=x(p.predicted), hi=y(p.ci[1]), lo=y(p.ci[0]);
    svg += `<path d="M${px} ${hi}V${lo}M${px-4} ${hi}H${px+4}M${px-4} ${lo}H${px+4}" stroke="#8bbcac" stroke-width="1.4"/><circle cx="${px}" cy="${y(p.observed)}" r="4.4" fill="#288978" stroke="white" stroke-width="1.5"><title>Predicted ${percent(p.predicted)}, observed ${percent(p.observed)}; n=${p.n}; 95% interval ${interval(p.ci,true)}</title></circle>`;
  });
  return svg + "</svg>";
}

function render(result) {
  const m = result.overall;
  $("auroc").textContent = number(m.auroc);
  $("auc-ci").textContent = m.auroc_ci ? `${interval(m.auroc_ci)} · 95% CI` : "Requires both outcome classes";
  $("ap").textContent = number(m.average_precision);
  $("ap-baseline").textContent = `Prevalence baseline: ${percent(m.prevalence)}`;
  $("recall").textContent = percent(m.recall);
  $("recall-ci").textContent = m.recall_ci ? `${interval(m.recall_ci,true)} · 95% CI` : "No positive outcomes";
  $("brier").textContent = number(m.brier);
  for (const key of ["tp", "fp", "tn", "fn"]) $(key).textContent = m[key].toLocaleString();
  $("precision-summary").textContent = `Precision ${percent(m.precision)}`;
  $("specificity").textContent = `Specificity ${percent(m.specificity)} · Accuracy ${percent(m.accuracy)}`;
  $("dataset-name").textContent = state.name;
  $("dataset-details").textContent = `${m.n.toLocaleString()} patients · ${m.positives.toLocaleString()} positive outcomes · ${percent(m.prevalence)} prevalence`;
  $("source-tag").textContent = state.synthetic ? "SYNTHETIC DATA" : "YOUR PREDICTIONS";
  $("demo-note").hidden = !state.synthetic;
  $("calibration-chart").innerHTML = calibrationChart(result.calibration);
  $("group").replaceChildren(new Option("None", ""), ...result.available_groups.map(g=>new Option(g,g)));
  $("group").value = result.group || "";
  $("group-rows").innerHTML = result.subgroups.length ? result.subgroups.map(s=>`<tr><td>${esc(s.label)}${s.n < 30 || s.positives < 10 || s.n-s.positives < 10 ? '<small>Small sample · interpret cautiously</small>' : ""}</td><td>${s.n.toLocaleString()}</td><td>${s.positives.toLocaleString()}</td><td>${number(s.auroc)}<small>${interval(s.auroc_ci)}</small></td><td>${percent(s.recall)}<small>${interval(s.recall_ci,true)}</small></td><td>${percent(s.precision)}</td><td>${number(s.brier)}</td></tr>`).join("") : '<tr><td colspan="7">Select a subgroup column to compare patients. Include categorical columns in your CSV to enable this view.</td></tr>';
  $("warnings").replaceChildren(...result.warnings.map(w=>{const p=document.createElement("p");p.textContent=w;return p;}));
  $("method-text").textContent=result.methods;
  $("threshold").value=result.threshold;
  $("threshold-output").textContent=result.threshold.toFixed(2);
}

function busy(value) {
  $("export").disabled=value || !state.result;
  $("status").textContent=value ? "Calculating confidence intervals…" : state.result ? "Evaluation ready · 95% intervals" : "Import predictions or load the demo";
}

async function run(csv=state.csv, name=state.name, synthetic=state.synthetic, group=$("group").value, threshold=Number($("threshold").value)) {
  const seq=++state.seq;
  busy(true); $("error").hidden=true; $("export-ready").hidden=true;
  try {
    const response=await fetch("/api/evaluate", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({csv,threshold,group})});
    const result=await response.json();
    if (!response.ok) throw new Error(result.error || "Could not evaluate this dataset.");
    if(seq!==state.seq)return;
    Object.assign(state,{csv,name,synthetic,result});
    render(result);
  } catch(error) {
    if(seq!==state.seq)return;
    $("error").textContent=error.message;$("error").hidden=false;
    if(state.result)render(state.result);
  } finally {if(seq===state.seq)busy(false);}
}

async function loadDemo() {
  clearTimeout(state.timer);
  try {
    const response=await fetch("/api/demo");
    if(!response.ok)throw new Error("Could not load the synthetic example.");
    await run(await response.text(),"Synthetic readmission demo",true,"age_group",0.5);
  } catch(error) {$("error").textContent=error.message;$("error").hidden=false;}
}

$("threshold").addEventListener("input",()=>{
  $("threshold-output").textContent=Number($("threshold").value).toFixed(2);
  clearTimeout(state.timer);state.seq++;busy(true);
  state.timer=setTimeout(()=>run(),220);
});
$("group").addEventListener("change",()=>{clearTimeout(state.timer);run();});
$("demo").addEventListener("click",loadDemo);
$("import").addEventListener("click",()=>$("upload").click());
document.querySelector('a[href="#methods"]').addEventListener("click",()=>{$("methods").open=true;});
$("upload").addEventListener("change",async event=>{
  const file=event.target.files[0];
  if(!file)return;
  clearTimeout(state.timer);
  if(file.size>8*1024*1024){$("error").textContent="CSV is too large. Maximum size is 8 MB.";$("error").hidden=false;}
  else await run(await file.text(),file.name,false,"",0.5);
  event.target.value="";
});
$("export").addEventListener("click",async()=>{
  if(!state.result)return;
  $("export").disabled=true;
  try {
    const response=await fetch("/api/export",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({csv:state.csv,threshold:state.result.threshold,group:state.result.group})});
    if(!response.ok){const result=await response.json();throw new Error(result.error || "Could not export report.");}
    const {url}=await response.json();
    $("report-download").href=url+"?download=1";
    $("report-preview").href=url;
    $("export-ready").hidden=false;
    $("report-download").click();
  } catch(error){$("error").textContent=error.message;$("error").hidden=false;}
  finally{$("export").disabled=false;}
});
loadDemo();
