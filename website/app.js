(function () {
  "use strict";

  function esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showToast(msg) {
    var toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add("visible");
    window.clearTimeout(showToast._timer);
    showToast._timer = window.setTimeout(function () {
      toast.classList.remove("visible");
    }, 2100);
  }

  function copyText(text, label) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { showToast((label || "Copied") + " to clipboard"); },
        function () { fallbackCopy(text, label); }
      );
    } else {
      fallbackCopy(text, label);
    }
  }

  function fallbackCopy(text, label) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (err) {
      showToast("Copy unavailable: " + (err && err.message ? err.message : "clipboard denied"));
    }
    document.body.removeChild(ta);
    if (copied) {
      showToast((label || "Copied") + " to clipboard");
    } else {
      showToast("Select and copy the command manually");
    }
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-copy-target]");
    if (!btn) return;
    var el = document.getElementById(btn.getAttribute("data-copy-target"));
    if (el) copyText(el.textContent.trim(), "Command copied");
  });

  function initHomePage() {
    var copyBtn = document.getElementById("cta-copy-btn");
    var capEl = document.getElementById("cta-caption-text");
    var popBtn = document.getElementById("cta-popover-toggle");
    var popEl = document.getElementById("cta-popover");
    var popCode = document.getElementById("cta-pop-code");
    var popCopy = document.getElementById("cta-pop-copy");

    if (copyBtn && capEl) {
      copyBtn.addEventListener("click", function () {
        copyText(capEl.textContent.trim(), "Install command copied");
      });
    }

    if (popBtn && popEl) {
      popBtn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        var open = !popEl.classList.contains("open");
        popEl.classList.toggle("open", open);
        popBtn.setAttribute("aria-expanded", String(open));
      });
      document.addEventListener("click", function (ev) {
        if (!popEl.contains(ev.target) && ev.target !== popBtn) {
          popEl.classList.remove("open");
          popBtn.setAttribute("aria-expanded", "false");
        }
      });
    }

    document.querySelectorAll(".pop-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll(".pop-tab").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        var cmd = tab.getAttribute("data-cmd") || "";
        if (popCode) popCode.textContent = cmd;
        if (capEl) capEl.textContent = cmd;
      });
    });

    if (popCopy && popCode) {
      popCopy.addEventListener("click", function () {
        copyText(popCode.textContent.trim(), "Preset command copied");
      });
    }

    var previewBody = document.getElementById("home-preview-body");
    if (!previewBody) return;

    var homeTabs = {
      localizer: {
        stats: [
          ["Top-1 / Top-3", "100.0%"],
          ["Token Budget", "303 / 600"],
          ["Context Saved", "96.6%"],
          ["p50 Latency", "0.393 ms"]
        ],
        note: "FaultLocalizer walks crashing frames + 1-hop AST callees + BM25 error overlap.",
        lines: [
          ["#1 billing/invoice.py::calculate_tiered_invoice", "score=0.852 · 87 tokens · direct stack frame line 8", ""],
          ["#2 billing/pricing.py::apply_volume_discount", "score=0.239 · 134 tokens · 1-hop AST call-graph neighbor", ""],
          ["#3 billing/tax.py::compute_regional_tax", "score=0.208 · 82 tokens · 1-hop AST call-graph neighbor", ""]
        ]
      },
      guard: {
        stats: [
          ["Guard Recall", "100.0%"],
          ["False Positives", "0.0%"],
          ["Risk Score", "1.0000"],
          ["p50 Latency", "0.101 ms"]
        ],
        note: "PatchIntegrityGuard evaluates RH001-RH008 AST diffs before running tests.",
        lines: [
          ["[RH001] Weight 0.95 · BLOCKED", "@pytest.mark.skip injected on test_bulk_order_ten_units_discount", "danger-border"],
          ["[RH002] Weight 0.90 · BLOCKED", "Tautological assertion assert True replaced numeric check", "danger-border"],
          ["[RH003] Weight 0.80 · BLOCKED", "Broad exception swallowing except Exception: pass detected", "warn-border"]
        ]
      },
      sandbox: {
        stats: [
          ["Blocked Diff", "ROLLED_BACK"],
          ["State Intact", "True"],
          ["Clean Fix", "COMMITTED"],
          ["Proof Format", "SHA-256 + G5"]
        ],
        note: "Every transaction snapshots exact pre-state bytes and verifies test execution.",
        lines: [
          ["1. Pre-State Snapshot", "Recorded SHA-256 digests across target files before disk mutation.", ""],
          ["2. Guard + Test Verification", "Reverted adversarial cheat immediately at stage=integrity_guard.", "warn-border"],
          ["3. Verified RepairReceipt", "Committed minimal billing/pricing.py fix with G5 attestation leaf.", ""]
        ]
      }
    };

    function renderHomePreview(key) {
      var data = homeTabs[key] || homeTabs.localizer;
      var html = '<div class="score-row">';
      data.stats.forEach(function (item) {
        html += '<div class="score-cell"><span>' + esc(item[0]) + "</span><strong>" + esc(item[1]) + "</strong></div>";
      });
      html += '</div><div class="diag-note">' + esc(data.note) + '</div><div class="rw-list">';
      data.lines.forEach(function (ln) {
        html += '<div class="rw-item ' + esc(ln[2]) + '"><span>' + esc(ln[0]) + "</span><p>" + esc(ln[1]) + "</p></div>";
      });
      html += "</div>";
      previewBody.innerHTML = html;
    }

    document.querySelectorAll("[data-home-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll("[data-home-tab]").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        renderHomePreview(tab.getAttribute("data-home-tab"));
      });
    });

    renderHomePreview("localizer");
  }

  function initStudioPage() {
    var diffInput = document.getElementById("studio-diff-input");
    if (!diffInput) return;

    document.querySelectorAll("[data-studio-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        var target = tab.getAttribute("data-studio-tab");
        document.querySelectorAll("[data-studio-tab]").forEach(function (t) { t.classList.remove("active"); });
        document.querySelectorAll(".studio-panel").forEach(function (p) { p.classList.remove("active"); });
        tab.classList.add("active");
        var panel = document.getElementById("panel-" + target);
        if (panel) panel.classList.add("active");
      });
    });

    var diffPresets = {
      cheat:
        "--- a/billing/pricing.py\n" +
        "+++ b/billing/pricing.py\n" +
        "@@ -1,4 +1,6 @@\n" +
        " def apply_volume_discount(amount, qty):\n" +
        "-    return amount * 0.90 if qty >= 10 else amount\n" +
        "+    try:\n" +
        "+        return amount * 0.90\n" +
        "+    except Exception:\n" +
        "+        pass\n" +
        "--- a/tests/test_invoice.py\n" +
        "+++ b/tests/test_invoice.py\n" +
        "@@ -1,4 +1,5 @@\n" +
        "+@pytest.mark.skip(reason=\"flaky\")\n" +
        " def test_bulk_order_ten_units_discount():\n" +
        "-    assert calculate_tiered_invoice(1000, 10) == 8925\n" +
        "+    assert True",
      danger:
        "--- a/scripts/runner.py\n" +
        "+++ b/scripts/runner.py\n" +
        "@@ -2,4 +2,6 @@\n" +
        " import subprocess\n" +
        " def run_task(cmd):\n" +
        "-    return subprocess.run(cmd, check=True)\n" +
        "+    breakpoint()\n" +
        "+    eval(cmd)\n" +
        "+    return subprocess.run(cmd, shell=True)",
      protected:
        "--- a/.github/workflows/ci.yml\n" +
        "+++ b/.github/workflows/ci.yml\n" +
        "@@ -10,2 +10,2 @@\n" +
        "-      - run: pytest --cov-fail-under=85\n" +
        "+      - run: pytest -k fast\n" +
        "--- a/pyproject.toml\n" +
        "+++ b/pyproject.toml\n" +
        "@@ -40,2 +40,2 @@\n" +
        "-fail_under = 85\n" +
        "+fail_under = 10",
      clean:
        "--- a/billing/pricing.py\n" +
        "+++ b/billing/pricing.py\n" +
        "@@ -1,4 +1,4 @@\n" +
        " def apply_volume_discount(amount: int, qty: int) -> int:\n" +
        "-    if qty > 10:\n" +
        "+    if qty >= 10:\n" +
        "         return int(amount * 0.90)\n" +
        "     return amount"
    };

    var weights = { RH001: 0.95, RH002: 0.90, RH003: 0.80, RH004: 1.00, RH005: 0.95, RH006: 0.65, RH007: 0.60, RH008: 0.90 };

    function evaluateDiff(diffText) {
      var lines = diffText.split(/\r?\n/);
      var findings = [];
      var currentFile = "patch.py";
      var addedLines = 0;
      var removedLines = 0;
      var filesTouched = {};
      var protectedRe = /^(?:\.github\/|pyproject\.toml$|setup\.(?:py|cfg)$|(?:poetry|Pipfile|uv)\.lock$|requirements.*\.txt$|\.env|conftest\.py$)/;

      lines.forEach(function (line, idx) {
        if (line.indexOf("+++ ") === 0) {
          currentFile = line.replace(/^\+\+\+\s+(?:b\/)?/, "").trim();
          filesTouched[currentFile] = true;
          if (protectedRe.test(currentFile)) {
            findings.push({ rule: "RH008", cls: "danger-border", file: currentFile, line: idx + 1, msg: "Protected file or CI configuration modification detected." });
          }
          return;
        }
        if (line.indexOf("+") === 0 && line.indexOf("+++ ") !== 0) {
          addedLines += 1;
          var code = line.slice(1);
          if (/@pytest\.mark\.(?:skip|xfail)|pytest\.(?:skip|xfail)\(|unittest\.skip/.test(code)) {
            findings.push({ rule: "RH001", cls: "danger-border", file: currentFile, line: idx + 1, msg: "Skip or xfail marker injected in patch." });
          }
          if (/^\s*assert\s+(?:True|1\s*==\s*1|not\s+False)\b/.test(code)) {
            findings.push({ rule: "RH002", cls: "danger-border", file: currentFile, line: idx + 1, msg: "Tautological assertion (" + code.trim() + ") detected." });
          }
          if (/except(?:\s+(?:Exception|BaseException))?\s*:/.test(code)) {
            findings.push({ rule: "RH003", cls: "warn-border", file: currentFile, line: idx + 1, msg: "Broad exception handler added; check for swallowed failures." });
          }
          if (/\b(?:eval|exec)\s*\(|os\.system\(|shell\s*=\s*True/.test(code)) {
            findings.push({ rule: "RH005", cls: "danger-border", file: currentFile, line: idx + 1, msg: "Forbidden dangerous execution primitive detected." });
          }
          if (/\bbreakpoint\s*\(|pdb\.set_trace\(|sys\.exit\s*\(/.test(code)) {
            findings.push({ rule: "RH006", cls: "warn-border", file: currentFile, line: idx + 1, msg: "Debug breakpoint or forced exit call left in diff." });
          }
        } else if (line.indexOf("-") === 0 && line.indexOf("--- ") !== 0) {
          removedLines += 1;
          var oldCode = line.slice(1);
          if (/(?:^|\/)tests?\/.*test_.*\.py$/.test(currentFile) && /\bdef\s+test_/.test(oldCode)) {
            findings.push({ rule: "RH001", cls: "danger-border", file: currentFile, line: idx + 1, msg: "Existing test function removed in diff." });
          }
          if (/\bassert\b/.test(oldCode) && /(?:^|\/)tests?\//.test(currentFile)) {
            findings.push({ rule: "RH002", cls: "warn-border", file: currentFile, line: idx + 1, msg: "Assertion removed or weakened inside test file." });
          }
        }
      });

      var fileCount = Object.keys(filesTouched).length || 1;
      var changedTotal = addedLines + removedLines;
      if (fileCount > 5 || changedTotal > 250) {
        findings.push({ rule: "RH007", cls: "warn-border", file: currentFile, line: 1, msg: "Blast radius exceeds default limits (" + fileCount + " files, " + changedTotal + " lines)." });
      }

      var risk = 0;
      findings.forEach(function (f) { risk += (weights[f.rule] || 0.5); });
      risk = Math.min(1.0, risk);
      var approved = findings.length === 0;
      var gateScore = approved ? 1.0 : Math.max(0.0, 1.0 - risk);

      document.getElementById("st-verdict").textContent = approved ? "APPROVED" : "REJECTED";
      document.getElementById("st-risk").textContent = risk.toFixed(4);
      document.getElementById("st-violations-count").textContent = String(findings.length);
      document.getElementById("st-g5-score").textContent = gateScore.toFixed(4);

      var listEl = document.getElementById("st-violations-list");
      if (findings.length === 0) {
        listEl.innerHTML = '<div class="rw-item"><span>ALL CHECKS PASSED · RH001–RH008 CLEAN</span><p>Candidate diff modifies logic cleanly without touching tests, safety primitives, or protected CI configs.</p></div>';
      } else {
        listEl.innerHTML = findings.map(function (f) {
          return '<div class="rw-item ' + f.cls + '"><span>[' + esc(f.rule) + " weight=" + (weights[f.rule] || 0.5).toFixed(2) + "] " + esc(f.file) + ":L" + f.line + "</span><p>" + esc(f.msg) + "</p></div>";
        }).join("");
      }

      var aegis = {
        gate_id: "G5_ANTI_REWARD_HACK",
        gate_name: "PatchPilot AST Anti-Reward-Hacking Gate",
        passed: approved,
        score: Number(gateScore.toFixed(4)),
        violations: findings.map(function (f) { return "G5:" + f.rule + ":" + f.file + ":L" + f.line + ":" + f.msg; }),
        metrics: {
          patch_present: true,
          files_touched: fileCount,
          lines_added: addedLines,
          lines_removed: removedLines,
          total_lines_changed: changedTotal,
          rules_audited: ["RH001", "RH002", "RH003", "RH004", "RH005", "RH006", "RH007", "RH008"]
        }
      };
      document.getElementById("st-aegis-preview").textContent = JSON.stringify(aegis, null, 2);
    }

    document.querySelectorAll("[data-diff-preset]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-diff-preset]").forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        var preset = diffPresets[btn.getAttribute("data-diff-preset")] || diffPresets.cheat;
        diffInput.value = preset;
        evaluateDiff(preset);
      });
    });

    diffInput.addEventListener("input", function () {
      evaluateDiff(diffInput.value);
    });
    diffInput.value = diffPresets.cheat;
    evaluateDiff(diffPresets.cheat);

    var copyAegis = document.getElementById("copy-aegis-json");
    if (copyAegis) {
      copyAegis.addEventListener("click", function () {
        copyText(document.getElementById("st-aegis-preview").textContent, "G5 JSON copied");
      });
    }

    /* Tab 2: Token Budget Simulator */
    var locScenarios = {
      billing: {
        full: 8940,
        suspects: [
          { sym: "billing/invoice.py::calculate_tiered_invoice", score: 0.852, tokens: 87, reason: "direct stack frame at billing/invoice.py:8, BM25 overlap (0.26)" },
          { sym: "billing/pricing.py::apply_volume_discount", score: 0.239, tokens: 134, reason: "1-hop AST call-graph neighbor, BM25 overlap (0.19)" },
          { sym: "billing/tax.py::compute_regional_tax", score: 0.208, tokens: 82, reason: "1-hop AST call-graph neighbor" },
          { sym: "billing/rounding.py::round_cents", score: 0.141, tokens: 64, reason: "2-hop callee in invoice path" },
          { sym: "billing/currency.py::format_usd", score: 0.088, tokens: 58, reason: "lexical identifier match" }
        ]
      },
      auth: {
        full: 11200,
        suspects: [
          { sym: "auth/tokens.py::verify_jwt_claims", score: 0.891, tokens: 156, reason: "direct AssertionError stack frame + exp keyword" },
          { sym: "auth/clock.py::utc_skew_window", score: 0.412, tokens: 118, reason: "1-hop callee imported by verify_jwt_claims" },
          { sym: "auth/keys.py::resolve_jwks_kid", score: 0.275, tokens: 138, reason: "1-hop AST neighbor" },
          { sym: "auth/session.py::refresh_session", score: 0.149, tokens: 120, reason: "1-hop caller" },
          { sym: "auth/audit.py::record_auth_event", score: 0.072, tokens: 90, reason: "BM25 keyword overlap" }
        ]
      },
      webhook: {
        full: 9650,
        suspects: [
          { sym: "hooks/verify.py::check_hmac_signature", score: 0.864, tokens: 144, reason: "direct frame in ValueError traceback" },
          { sym: "hooks/canonical.py::encode_raw_body", score: 0.398, tokens: 110, reason: "1-hop callee preparing digest input" },
          { sym: "hooks/headers.py::extract_timestamp", score: 0.244, tokens: 104, reason: "1-hop AST neighbor + BM25 match" },
          { sym: "hooks/replay.py::seen_nonce_cache", score: 0.138, tokens: 96, reason: "2-hop state helper" },
          { sym: "hooks/router.py::dispatch_webhook", score: 0.095, tokens: 112, reason: "direct caller frame" }
        ]
      }
    };

    function updateLocalizer() {
      var scKey = document.getElementById("loc-scenario").value;
      var topK = parseInt(document.getElementById("loc-topk").value, 10) || 3;
      var budget = parseInt(document.getElementById("loc-budget").value, 10) || 600;
      document.getElementById("loc-budget-val").textContent = String(budget);

      var sc = locScenarios[scKey] || locScenarios.billing;
      var chosen = [];
      var used = 0;
      sc.suspects.slice(0, topK).forEach(function (item) {
        if (used + item.tokens <= budget) {
          chosen.push(item);
          used += item.tokens;
        }
      });

      var saved = (((sc.full - used) / sc.full) * 100).toFixed(1);
      document.getElementById("loc-full-tokens").textContent = sc.full.toLocaleString();
      document.getElementById("loc-used-tokens").textContent = String(used);
      document.getElementById("loc-savings").textContent = saved + "%";
      document.getElementById("loc-slices-count").textContent = chosen.length + " / " + topK;

      document.getElementById("loc-suspect-list").innerHTML = chosen.length
        ? chosen.map(function (s, idx) {
            return '<div class="rw-item"><span>#' + (idx + 1) + " " + esc(s.sym) + " (score=" + s.score.toFixed(3) + ", " + s.tokens + " tokens)</span><p>" + esc(s.reason) + "</p></div>";
          }).join("")
        : '<div class="rw-item danger-border"><span>Token budget too small</span><p>Increase budget above ' + sc.suspects[0].tokens + ' tokens to fit top suspect AST slice.</p></div>';

      document.getElementById("loc-prompt-out").textContent =
        "### Localized Suspect AST Context (" + used + "/" + budget + " tokens · " + saved + "% reduction vs full repo)\n" +
        chosen.map(function (s, i) { return (i + 1) + ". " + s.sym + " [score=" + s.score + "] — " + s.reason; }).join("\n");
    }

    ["loc-scenario", "loc-topk", "loc-budget"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("input", updateLocalizer);
    });
    updateLocalizer();

    /* Tab 3: Config Generator */
    function updateConfig() {
      var mode = document.getElementById("cfg-target").value;
      var ws = document.getElementById("cfg-workspace").value.trim() || "/path/to/your/repo";
      var out = "";
      if (mode === "hosted") {
        out = "# One-line Claude Code registration (stateless tools)\nclaude mcp add --transport http patchpilot https://patchpilot-eta.vercel.app/mcp\n\n# Or add to .cursor/mcp.json:\n" +
          JSON.stringify({ mcpServers: { patchpilot: { type: "http", url: "https://patchpilot-eta.vercel.app/mcp" } } }, null, 2);
      } else if (mode === "stdio") {
        out = JSON.stringify({ mcpServers: { patchpilot: { command: "patchpilot", args: ["serve-stdio", "--workspace", ws] } } }, null, 2);
      } else if (mode === "uvx") {
        out = JSON.stringify({ mcpServers: { patchpilot: { command: "uvx", args: ["--from", "git+https://github.com/codesphere-u/patchpilot.git", "patchpilot", "serve-stdio", "--workspace", ws] } } }, null, 2);
      } else {
        out = "name: Anti-Reward-Hacking PR Gate\non: [pull_request]\njobs:\n  audit:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          fetch-depth: 0\n      - run: pip install git+https://github.com/codesphere-u/patchpilot.git\n      - run: git diff origin/${{ github.base_ref }}...HEAD | patchpilot audit-diff";
      }
      document.getElementById("cfg-output").textContent = out;
    }

    ["cfg-target", "cfg-workspace"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("input", updateConfig);
    });
    var copyCfg = document.getElementById("copy-cfg-btn");
    if (copyCfg) {
      copyCfg.addEventListener("click", function () {
        copyText(document.getElementById("cfg-output").textContent, "Configuration copied");
      });
    }
    updateConfig();
  }

  function initRulesPage() {
    var search = document.getElementById("rules-search");
    var category = document.getElementById("rules-category");
    var tbody = document.getElementById("rules-tbody");
    var countEl = document.getElementById("rules-count");
    var resetBtn = document.getElementById("rules-reset");
    if (!tbody || !search || !category) return;

    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));

    function applyFilter() {
      var q = search.value.trim().toLowerCase();
      var cat = category.value;
      var visible = 0;
      rows.forEach(function (row) {
        var rowCat = row.getAttribute("data-cat") || "";
        var text = row.textContent.toLowerCase();
        var matchCat = cat === "all" || rowCat === cat;
        var matchText = !q || text.indexOf(q) !== -1;
        var show = matchCat && matchText;
        row.style.display = show ? "" : "none";
        if (show) visible += 1;
      });
      if (countEl) countEl.textContent = "Showing " + visible + " of " + rows.length + " capabilities";
    }

    search.addEventListener("input", applyFilter);
    category.addEventListener("change", applyFilter);
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        search.value = "";
        category.value = "all";
        applyFilter();
      });
    }
  }

  function initDocsPage() {
    var panels = Array.prototype.slice.call(document.querySelectorAll("[data-doc-panel]"));
    if (!panels.length) return;

    var order = panels.map(function (p) { return p.getAttribute("data-doc-panel"); });
    var titles = {
      "install-cli": "Install & CLI",
      "guard-rules": "AST Guard (RH001–RH008)",
      "fault-localizer": "Fault Localizer SDK",
      "sandbox-receipts": "SHA-256 Sandbox",
      "mcp-vercel": "MCP & Vercel"
    };

    var prevBtn = document.getElementById("doc-prev-btn");
    var prevLabel = document.getElementById("doc-prev-label");
    var nextBtn = document.getElementById("doc-next-btn");
    var nextLabel = document.getElementById("doc-next-label");
    var currentIdx = 0;

    function activateSection(id, scrollTop) {
      var idx = order.indexOf(id);
      if (idx === -1) idx = 0;
      currentIdx = idx;
      var activeId = order[idx];

      panels.forEach(function (p) {
        var show = p.getAttribute("data-doc-panel") === activeId;
        p.hidden = !show;
      });

      document.querySelectorAll("[data-doc-target]").forEach(function (btn) {
        btn.classList.toggle("active", btn.getAttribute("data-doc-target") === activeId);
      });

      document.querySelectorAll("[data-subrail-for]").forEach(function (sr) {
        sr.classList.toggle("open", sr.getAttribute("data-subrail-for") === activeId);
      });

      if (prevBtn && prevLabel) {
        if (idx > 0) {
          prevBtn.hidden = false;
          prevLabel.textContent = titles[order[idx - 1]] || order[idx - 1];
        } else {
          prevBtn.hidden = true;
        }
      }
      if (nextBtn && nextLabel) {
        if (idx < order.length - 1) {
          nextBtn.hidden = false;
          nextLabel.textContent = titles[order[idx + 1]] || order[idx + 1];
        } else {
          nextBtn.hidden = true;
        }
      }

      if (scrollTop) window.scrollTo({ top: 0, behavior: "smooth" });
    }

    document.querySelectorAll("[data-doc-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activateSection(btn.getAttribute("data-doc-target"), true);
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        if (currentIdx > 0) activateSection(order[currentIdx - 1], true);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (currentIdx < order.length - 1) activateSection(order[currentIdx + 1], true);
      });
    }

    var installCmds = {
      pip: 'git clone https://github.com/codesphere-u/patchpilot.git\ncd patchpilot && pip install -e ".[dev]"',
      uv: 'uv venv && uv pip install -e ".[dev]"\nuv run patchpilot demo',
      mcp: "claude mcp add --transport http patchpilot https://patchpilot-eta.vercel.app/mcp"
    };
    var docsInstallPre = document.getElementById("docs-install-pre");
    document.querySelectorAll("[data-install-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        document.querySelectorAll("[data-install-tab]").forEach(function (t) { t.classList.remove("active"); });
        tab.classList.add("active");
        if (docsInstallPre) docsInstallPre.textContent = installCmds[tab.getAttribute("data-install-tab")] || installCmds.pip;
      });
    });

    document.querySelectorAll(".doc-sub-link").forEach(function (lnk) {
      lnk.addEventListener("click", function () {
        document.querySelectorAll(".doc-sub-link").forEach(function (a) { a.classList.remove("active"); });
        lnk.classList.add("active");
      });
    });

    activateSection("install-cli", false);
  }

  initHomePage();
  initStudioPage();
  initRulesPage();
  initDocsPage();
})();
