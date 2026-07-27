(function () {
  const STORAGE_KEY = "design-daily-feedback-v1";
  const config = window.__FEEDBACK_CONFIG__ || {};

  function emptyState() {
    return {
      version: 1,
      actor_id: crypto.randomUUID ? crypto.randomUUID() : `actor-${Date.now()}`,
      decisions: {},
      pending: [],
    };
  }

  function load() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      return parsed && parsed.version === 1 ? parsed : emptyState();
    } catch (error) {
      return emptyState();
    }
  }

  function save(value) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  }

  function itemSnapshot(item) {
    return {
      title: item.title || "",
      category: item.category || "",
      summary: item.summary || "",
      url: item.url || "",
      source_name: item.source_name || item.source || "",
      source_family: item.source_family || "",
      action_lane: item.action_lane || "",
      axes: (item.axes || []).slice(0, 3),
      tags: (item.tags || []).slice(0, 6),
    };
  }

  function decision(productId) {
    return load().decisions[String(productId)] || null;
  }

  function record(item, action, reason, context) {
    const value = load();
    const productId = String(item.id || item.url || item.title);
    const event = {
      event_id: crypto.randomUUID ? crypto.randomUUID() : `feedback-${Date.now()}-${productId}`,
      workspace: config.workspace || "design-daily",
      actor_id: value.actor_id,
      product_id: productId,
      action,
      reason: reason || "",
      context: context || {},
      item_snapshot: itemSnapshot(item),
      created_at: new Date().toISOString(),
    };
    value.decisions[productId] = event;
    value.pending.push(event);
    save(value);
    window.dispatchEvent(new CustomEvent("feedback:change", { detail: event }));
    flush();
    return event;
  }

  function clear(productId) {
    const value = load();
    productId = String(productId);
    const previous = value.decisions[productId];
    if (!previous) return;
    const event = {
      ...previous,
      event_id: crypto.randomUUID ? crypto.randomUUID() : `feedback-${Date.now()}-${productId}`,
      action: "clear",
      reason: "",
      created_at: new Date().toISOString(),
    };
    delete value.decisions[productId];
    value.pending.push(event);
    save(value);
    window.dispatchEvent(new CustomEvent("feedback:change", { detail: event }));
    flush();
  }

  function summary(items) {
    const decisions = load().decisions;
    const result = { reviewed: 0, like: 0, pass: 0, pending: load().pending.length };
    items.forEach(item => {
      const event = decisions[String(item.id || item.url || item.title)];
      if (!event) return;
      result.reviewed += 1;
      if (event.action === "like") result.like += 1;
      if (event.action === "pass") result.pass += 1;
    });
    return result;
  }

  async function flush() {
    const supabaseReady = config.supabaseUrl && config.publishableKey;
    if (!config.endpoint && !supabaseReady) return;
    const value = load();
    if (!value.pending.length) return;
    const batch = value.pending.slice(0, 50);
    try {
      const sent = new Set();
      if (supabaseReady) {
        const endpoint = `${config.supabaseUrl.replace(/\/$/, "")}/rest/v1/${config.table || "feedback_events"}`;
        for (const event of batch) {
          const response = await fetch(endpoint, {
            method: "POST",
            headers: {
              apikey: config.publishableKey,
              "Content-Type": "application/json",
              Prefer: "return=minimal",
            },
            body: JSON.stringify(event),
          });
          if (!response.ok && response.status !== 409) {
            throw new Error(`feedback sync failed: ${response.status}`);
          }
          sent.add(event.event_id);
        }
      } else {
        const response = await fetch(config.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workspace: config.workspace || "design-daily", events: batch }),
        });
        if (!response.ok) throw new Error(`feedback sync failed: ${response.status}`);
        batch.forEach(event => sent.add(event.event_id));
      }
      const latest = load();
      latest.pending = latest.pending.filter(event => !sent.has(event.event_id));
      save(latest);
      window.dispatchEvent(new CustomEvent("feedback:sync"));
    } catch (error) {
      console.warn(error);
    }
  }

  window.FeedbackStore = { decision, record, clear, summary, flush };
  window.addEventListener("online", flush);
  window.setTimeout(flush, 0);
})();
