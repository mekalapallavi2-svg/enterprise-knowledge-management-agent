// Frontend coordinator for FastAPI Agent Orchestrator Dashboard
document.addEventListener("DOMContentLoaded", () => {
  const queryInput = document.getElementById("query-input");
  const analyzeBtn = document.getElementById("analyze-btn");
  const presetChips = document.querySelectorAll(".preset-chip");
  const groqKeyInput = document.getElementById("groq-key-input");
  const saveKeyBtn = document.getElementById("save-key-btn");
  const hallucinationToggle = document.getElementById("hallucination-toggle");
  const audienceSelect = document.getElementById("audience-select");
  
  const dbTabBtns = document.querySelectorAll(".db-tab-btn");
  const dbTabBrowse = document.getElementById("db-tab-browse");
  const dbTabIndex = document.getElementById("db-tab-index");
  const docList = document.getElementById("doc-list");
  
  const indexForm = document.getElementById("index-doc-form");
  const indexStatus = document.getElementById("index-status");
  
  const responsePanel = document.getElementById("response-panel");
  const responseBody = document.getElementById("response-body");
  const confBadge = document.getElementById("conf-badge");
  const copyBtn = document.getElementById("copy-btn");
  
  const valSummary = document.getElementById("val-summary");
  const valTitleStatus = document.getElementById("val-title-status");
  const valNotes = document.getElementById("val-notes");
  const valScore = document.getElementById("val-score");
  const valShield = document.getElementById("val-shield");
  
  const auditPanel = document.getElementById("audit-panel");
  const auditContent = document.getElementById("audit-content");
  
  const traceLogs = document.getElementById("trace-logs");
  const infoIntent = document.getElementById("info-intent");
  const infoEntities = document.getElementById("info-entities");
  const infoFilters = document.getElementById("info-filters");
  
  const svg = document.getElementById("pipeline-svg");

  const savedKey = sessionStorage.getItem("groq_api_key");
  if (savedKey && groqKeyInput) {
    groqKeyInput.value = savedKey;
  }

  if (groqKeyInput) {
    groqKeyInput.addEventListener("input", () => {
      const key = groqKeyInput.value.trim();
      if (key) {
        sessionStorage.setItem("groq_api_key", key);
      } else {
        sessionStorage.removeItem("groq_api_key");
      }
    });
  }

  if (saveKeyBtn) {
    saveKeyBtn.addEventListener("click", () => {
      const key = groqKeyInput.value.trim();
      if (key) {
        sessionStorage.setItem("groq_api_key", key);
        alert("Groq API Key saved successfully.");
      }
    });
  }

  dbTabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      dbTabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      
      const tab = btn.dataset.dbTab;
      if (tab === "browse") {
        dbTabBrowse.style.display = "block";
        dbTabIndex.style.display = "none";
        fetchDocuments();
      } else {
        dbTabBrowse.style.display = "none";
        dbTabIndex.style.display = "block";
      }
    });
  });

  presetChips.forEach(chip => {
    chip.addEventListener("click", () => {
      queryInput.value = chip.dataset.query;
    });
  });

  window.addEventListener("resize", drawConnectionLines);
  setTimeout(drawConnectionLines, 300);

  function getCenter(el) {
    const rect = el.getBoundingClientRect();
    const svgRect = svg.getBoundingClientRect();
    return {
      x: rect.left + rect.width / 2 - svgRect.left,
      y: rect.top + rect.height / 2 - svgRect.top
    };
  }

  function drawConnectionLines() {
    const nodes = {
      nlu: document.getElementById("node-nlu"),
      retrieval: document.getElementById("node-retrieval"),
      synthesis: document.getElementById("node-synthesis"),
      validation: document.getElementById("node-validation"),
      gap: document.getElementById("node-gap"),
      report: document.getElementById("node-report")
    };

    if (!nodes.nlu || !nodes.retrieval) return;

    const c = {
      nlu: getCenter(nodes.nlu),
      ret: getCenter(nodes.retrieval),
      synth: getCenter(nodes.synthesis),
      val: getCenter(nodes.validation),
      gap: getCenter(nodes.gap),
      rep: getCenter(nodes.report)
    };

    setPath("path-nlu-retrieval", c.nlu, c.ret);
    setPath("path-retrieval-synthesis", c.ret, c.synth);
    setPath("path-synthesis-validation", c.synth, c.val);
    setPath("path-validation-gap", c.val, c.gap);
    setPath("path-gap-report", c.gap, c.rep);
    setRetryPath("path-validation-retry", c.val, c.synth);
  }

  function setPath(id, from, to) {
    const path = document.getElementById(id);
    if (!path) return;
    path.setAttribute("d", `M ${from.x} ${from.y} L ${to.x} ${to.y}`);
  }

  function setRetryPath(id, from, to) {
    const path = document.getElementById(id);
    if (!path) return;
    const dx = from.x - to.x;
    const mx = to.x + dx / 2;
    const my = from.y - 45;
    path.setAttribute("d", `M ${from.x} ${from.y} Q ${mx} ${my} ${to.x} ${to.y}`);
  }

  async function fetchDocuments() {
    docList.innerHTML = '<div class="loading-spinner">Loading indexed records...</div>';
    try {
      const response = await fetch("/documents");
      if (!response.ok) throw new Error("Failed to load documents");
      
      const docs = await response.json();
      if (docs.length === 0) {
        docList.innerHTML = '<div class="empty-badge" style="padding: 20px; text-align: center;">No documents indexed in vector store.</div>';
        return;
      }

      docList.innerHTML = "";
      
      docs.forEach(doc => {
        const card = document.createElement("div");
        card.className = "doc-card";
        
        let displayTitle = doc.title;
        if (doc.title === "ACME Corp HR Leave Policy") {
          displayTitle = "Acme Corp Employee Leave Policy";
        } else if (doc.title === "ACME Corp Data Privacy Policy") {
          displayTitle = "Data Privacy & GDPR Policy";
        } else if (doc.title === "ACME Corp Corporate Employee Handbook") {
          displayTitle = "Corporate Employee Handbook";
        }

        const dept = (doc.metadata.department || "Human Resources").toUpperCase();
        
        // Strip headers, metadata, and markdown to show only clean policy text
        const contentStr = doc.content || "";
        const rawLines = contentStr.split("\n");
        const cleanLines = [];
        rawLines.forEach(line => {
          const trimmed = line.trim();
          if (trimmed.startsWith("#")) return;
          if (trimmed.includes("Document ID:") || 
              trimmed.includes("Last Updated:") || 
              trimmed.includes("Owner:") || 
              trimmed.includes("Department:") || 
              trimmed.includes("Status:")) {
            return;
          }
          if (!trimmed) return;
          cleanLines.push(trimmed);
        });
        
        let previewText = cleanLines.join(" ");
        previewText = previewText.replace(/\*\*/g, "").replace(/^\-\s+/g, "");
        if (previewText.length > 150) {
          previewText = previewText.substring(0, 150) + "...";
        }

        card.innerHTML = `
          <div class="doc-card-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <h3 style="font-size: 14px; font-weight: 600; color: var(--text-primary); max-width: 70%;">${displayTitle}</h3>
            <span class="doc-badge" style="background: rgba(236, 72, 153, 0.12); border: 1px solid rgba(236, 72, 153, 0.25); color: #ec4899; font-size: 9px; padding: 2px 6px; border-radius: 20px; font-weight: 600; text-transform: uppercase; white-space: nowrap;">${dept}</span>
          </div>
          <p class="doc-preview" style="font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin: 8px 0 10px;">${previewText}</p>
          <div class="doc-meta" style="margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 6px; display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted);">
            <span>Type: Policy</span>
            <span>Date: 2025-03-15</span>
          </div>
        `;
        docList.appendChild(card);
      });
    } catch (e) {
      docList.innerHTML = `<div class="empty-badge" style="color: #ef4444; padding: 20px;">Error loading database: ${e.message}</div>`;
    }
  }

  indexForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    indexStatus.className = "index-status-msg";
    indexStatus.textContent = "Uploading and chunking document...";
    
    const payload = {
      title: document.getElementById("doc-title").value,
      content: document.getElementById("doc-content").value,
      metadata: {
        department: document.getElementById("doc-dept").value,
        doc_type: document.getElementById("doc-type").value,
        author: document.getElementById("doc-author").value,
        date: new Date().toISOString().split('T')[0]
      }
    };

    try {
      const res = await fetch("/index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Index upload failed.");

      indexStatus.className = "index-status-msg success-text";
      indexStatus.innerHTML = `<span style="color: var(--color-validation)">&#x2714; Indexed successfully! ${data.chunk_count} chunks created.</span>`;
      indexForm.reset();
      
      setTimeout(() => {
        dbTabBtns[0].click();
      }, 1500);

    } catch (err) {
      indexStatus.className = "index-status-msg error-text";
      indexStatus.innerHTML = `<span style="color: #ef4444">&#x2718; Error: ${err.message}</span>`;
    }
  });

  function addTraceRow(time, agent, status, msg) {
    const row = document.createElement("div");
    row.className = `trace-log-row ${status.toLowerCase()}`;
    row.innerHTML = `
      <span class="trace-time">${time}</span>
      <span class="trace-agent">${agent}</span>
      <span class="trace-badge ${status.toLowerCase()}">${status}</span>
      <span class="trace-message">${msg}</span>
    `;
    traceLogs.appendChild(row);
    traceLogs.scrollTop = traceLogs.scrollHeight;
  }

  function setNodeVisual(agentId, state) {
    const node = document.getElementById(`node-${agentId}`);
    const statusLabel = document.getElementById(`status-${agentId}`);
    if (!node || !statusLabel) return;
    
    node.classList.remove("active", "completed", "retry-active");
    if (state === "ACTIVE") {
      node.classList.add("active");
      statusLabel.textContent = "THINKING";
    } else if (state === "COMPLETED") {
      node.classList.add("completed");
      statusLabel.textContent = "DONE";
    } else if (state === "RETRY") {
      node.classList.add("retry-active");
      statusLabel.textContent = "REVISING";
    } else {
      statusLabel.textContent = "IDLE";
    }
  }

  function setLineVisual(id, state) {
    const line = document.getElementById(id);
    if (!line) return;
    line.classList.remove("active", "completed");
    if (state === "ACTIVE") {
      line.classList.add("active");
      line.style.stroke = "var(--color-nlu)";
    } else if (state === "COMPLETED") {
      line.classList.add("completed");
      line.style.stroke = "var(--color-validation)";
    } else {
      line.style.stroke = "rgba(255,255,255,0.04)";
    }
  }

  function resetAllPipelineStates() {
    const agents = ["nlu", "retrieval", "synthesis", "validation", "gap", "report"];
    agents.forEach(a => setNodeVisual(a, "IDLE"));
    
    const lines = ["path-nlu-retrieval", "path-retrieval-synthesis", "path-synthesis-validation", "path-validation-gap", "path-gap-report", "path-validation-retry"];
    lines.forEach(l => setLineVisual(l, "IDLE"));
  }

  function renderMarkdown(md) {
    let html = md;
    html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^## (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    
    html = html.replace(/\|/g, ' ~CELL~ ');
    const lines = html.split('\n');
    let inTable = false;
    
    const processedLines = lines.map(line => {
      if (line.includes('~CELL~')) {
        const cells = line.split('~CELL~').map(c => c.trim()).filter(c => c !== "");
        if (line.includes('---')) return "";
        let row = '<tr>';
        cells.forEach(cell => {
          row += inTable ? `<td>${cell}</td>` : `<th>${cell}</th>`;
        });
        row += '</tr>';
        inTable = true;
        return row;
      } else {
        if (inTable) {
          inTable = false;
          return '</table>' + line;
        }
        return line;
      }
    });
    html = processedLines.join('\n');

    html = html.replace(/\[Source: (.*?), Section: (.*?)\]/g, '<span class="citation-ref" title="Double click to review matching document text">$1 ($2)</span>');
    html = html.replace(/\[Source: (.*?)\]/g, '<span class="citation-ref">$1</span>');
    html = html.replace(/\n\n/g, '<br><br>');
    return html;
  }

  analyzeBtn.addEventListener("click", async () => {
    const query = queryInput.value.trim();
    const apiKey = groqKeyInput.value.trim();
    
    if (!query) {
      alert("Please write a query.");
      return;
    }
    if (!apiKey) {
      alert("Please enter a valid Groq API Key first.");
      return;
    }

    resetAllPipelineStates();
    traceLogs.innerHTML = "";
    responsePanel.style.display = "none";
    auditPanel.style.display = "none";
    
    infoIntent.textContent = "Analyzing...";
    infoEntities.innerHTML = '<span class="empty-badge">Extracting...</span>';
    infoFilters.innerHTML = '<span class="empty-badge">Extracting...</span>';

    addTraceRow(new Date().toLocaleTimeString(), "System", "SUCCESS", `Received query: "${query}"`);
    
    const payload = {
      query: query,
      api_key: apiKey,
      audience: audienceSelect ? audienceSelect.value : "analyst",
      simulate_hallucination: hallucinationToggle ? hallucinationToggle.checked : false
    };

    try {
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = "Analyzing...";
      
      const response = await fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "API endpoint execution failed.");

      await animatePipelineTrace(data);
      
    } catch (err) {
      addTraceRow(new Date().toLocaleTimeString(), "System", "FAIL", `Error: ${err.message}`);
      alert(`Pipeline error: ${err.message}`);
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = `<span>Analyze Query</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`;
    }
  });

  async function animatePipelineTrace(data) {
    const delay = ms => new Promise(res => setTimeout(res, ms));
    const stepDuration = 900;
    
    const trace = data.trace;
    const finalResponse = data.response_text;
    const validation = data.validation;
    const chunks = data.chunks;

    infoIntent.textContent = data.intent;
    
    infoEntities.innerHTML = "";
    if (data.entities.length > 0) {
      data.entities.forEach(e => {
        infoEntities.innerHTML += `<span class="entity-chip">${e}</span>`;
      });
    } else {
      infoEntities.innerHTML = '<span class="empty-badge">None</span>';
    }

    infoFilters.innerHTML = "";
    const filterKeys = Object.keys(data.constraints).filter(k => data.constraints[k] !== null);
    if (filterKeys.length > 0) {
      filterKeys.forEach(k => {
        const valStr = typeof data.constraints[k] === 'object' ? JSON.stringify(data.constraints[k]) : data.constraints[k];
        infoFilters.innerHTML += `<span class="filter-chip">${k}: ${valStr}</span>`;
      });
    } else {
      infoFilters.innerHTML = '<span class="empty-badge">None</span>';
    }

    let prevAgent = null;

    for (let i = 0; i < trace.length; i++) {
      const step = trace[i];
      const time = step.timestamp || new Date().toLocaleTimeString();
      const agent = step.agent;
      const status = step.status;
      const msg = step.log;
      
      let nodeKey = "";
      if (agent.includes("Orchestrator")) nodeKey = "nlu";
      else if (agent.includes("Retrieval")) nodeKey = "retrieval";
      else if (agent.includes("Synthesis")) nodeKey = "synthesis";
      else if (agent.includes("Validation")) nodeKey = "validation";
      else if (agent.includes("Gap")) nodeKey = "gap";
      else if (agent.includes("Report")) nodeKey = "report";

      if (nodeKey) {
        if (prevAgent && prevAgent !== nodeKey) {
          setNodeVisual(prevAgent, "COMPLETED");
          const lineId = `path-${prevAgent}-${nodeKey}`;
          if (document.getElementById(lineId)) {
            setLineVisual(lineId, "COMPLETED");
          }
        }
        
        if (status === "RETRY") {
          setNodeVisual(nodeKey, "RETRY");
          setLineVisual("path-validation-retry", "ACTIVE");
          await delay(stepDuration);
          setLineVisual("path-validation-retry", "IDLE");
          setNodeVisual("synthesis", "ACTIVE");
        } else {
          setNodeVisual(nodeKey, "ACTIVE");
          if (prevAgent && prevAgent !== nodeKey) {
            const lineId = `path-${prevAgent}-${nodeKey}`;
            if (document.getElementById(lineId)) {
              setLineVisual(lineId, "ACTIVE");
            }
          }
        }
        
        prevAgent = nodeKey;
      }
      
      addTraceRow(time, agent, status, msg);
      await delay(stepDuration);
    }

    if (prevAgent) {
      setNodeVisual(prevAgent, "COMPLETED");
    }

    if (data.intent === "Report Generation") {
      setLineVisual("path-validation-gap", "COMPLETED");
      setLineVisual("path-gap-report", "COMPLETED");
      setNodeVisual("gap", "COMPLETED");
      setNodeVisual("report", "COMPLETED");
    }

    responsePanel.style.display = "block";
    responseBody.innerHTML = renderMarkdown(finalResponse);
    confBadge.textContent = `Confidence: ${chunks.length >= 3 ? "High" : chunks.length >= 1 ? "Medium" : "Low"}`;

    valSummary.className = "val-summary-badge";
    if (validation.validation_status === "PASS") {
      valSummary.classList.add("passed");
      valShield.textContent = "🛡️";
      valTitleStatus.textContent = "Validation: PASSED";
    } else if (validation.validation_status === "PASS_WITH_WARNINGS") {
      valSummary.classList.add("warning");
      valShield.textContent = "⚠️";
      valTitleStatus.textContent = "Validation: PASS WITH WARNINGS";
    } else {
      valSummary.classList.add("failed");
      valShield.textContent = "❌";
      valTitleStatus.textContent = "Validation: REJECTED & RESET";
    }
    
    valNotes.textContent = validation.validator_note;
    valScore.textContent = validation.score;

    const issues = validation.issues || [];
    const gapTrace = trace.find(t => t.agent.includes("Gap") && t.status === "SUCCESS");
    const gaps = gapTrace ? gapTrace.payload.gaps : [];

    if (issues.length > 0 || gaps.length > 0) {
      auditPanel.style.display = "block";
      auditContent.innerHTML = "";
      
      issues.forEach(issue => {
        const item = document.createElement("div");
        item.className = "audit-defect-card";
        item.innerHTML = `
          <div class="defect-header">
            <span class="defect-badge">${issue.issue_type}</span>
            <span style="font-size: 10px; color: var(--text-muted);">Validation Failure</span>
          </div>
          <div class="defect-location">"${issue.location}"</div>
          <div style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 4px;"><strong>Critique:</strong> ${issue.explanation}</div>
          <div class="defect-fix"><strong>Remediation Suggestion:</strong> ${issue.suggested_fix}</div>
        `;
        auditContent.appendChild(item);
      });

      gaps.forEach(gap => {
        const item = document.createElement("div");
        item.className = "audit-defect-card";
        item.style.borderColor = "rgba(245, 158, 11, 0.2)";
        item.style.background = "rgba(245, 158, 11, 0.03)";
        item.innerHTML = `
          <div class="defect-header">
            <span class="defect-badge" style="background: rgba(245,158,11,0.1); color: var(--color-gap); border-color: rgba(245,158,11,0.25);">${gap.gap_type}</span>
            <span style="font-size: 10px; color: var(--text-muted);">Priority: ${gap.impact_level}</span>
          </div>
          <div style="font-size: 13px; font-weight:600; margin-bottom: 4px; color: var(--text-primary);">${gap.topic}</div>
          <div style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 4px;"><strong>Action Required:</strong> ${gap.recommendation}</div>
          <div style="font-size: 11px; color: var(--text-muted);"><strong>Owner:</strong> ${gap.suggested_document_owner} | <strong>Timeline:</strong> ${gap.suggested_resolution_deadline}</div>
        `;
        auditContent.appendChild(item);
      });
    }

    const citations = responseBody.querySelectorAll(".citation-ref");
    citations.forEach(cit => {
      cit.addEventListener("click", () => {
        const text = cit.textContent;
        const match = chunks.find(ch => text.includes(ch.source_document) || ch.source_document.toLowerCase().includes(text.split("(")[0].trim().toLowerCase()));
        if (match) {
          alert(`Indexed Vector Chunk Details:\n\n[ID]: ${match.chunk_id}\n[Document]: ${match.source_document}\n[Section]: ${match.page_or_section}\n[Relevance Score]: ${match.relevance_score}\n\n[Grounded Text]: "${match.content}"`);
        }
      });
    });
  }

  copyBtn.addEventListener("click", () => {
    const text = responseBody.innerText;
    navigator.clipboard.writeText(text).then(() => {
      const originalText = copyBtn.textContent;
      copyBtn.textContent = "Copied!";
      setTimeout(() => {
        copyBtn.textContent = originalText;
      }, 1500);
    });
  });

  fetchDocuments();
});
