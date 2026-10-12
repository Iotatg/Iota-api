export class IotaClient {
  constructor({ baseUrl, apiKey = "" } = {}) {
    this.baseUrl = (baseUrl || "").replace(/\/$/, "");
    this.apiKey = apiKey;
  }

  headers() {
    const h = { "Content-Type": "application/json" };
    if (this.apiKey) h["X-API-Key"] = this.apiKey;
    return h;
  }

  async search(q, limit = 10) {
    const url = new URL(this.baseUrl + "/api/search");
    url.searchParams.set("q", q);
    url.searchParams.set("limit", String(limit));
    const res = await fetch(url);
    return res.json();
  }

  async insert(collection, document) {
    const res = await fetch(`${this.baseUrl}/api/v1/db/${collection}/insert`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(document),
    });
    return res.json();
  }

  async find(collection, query = {}) {
    const res = await fetch(`${this.baseUrl}/api/v1/db/${collection}/find`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(query),
    });
    return res.json();
  }
}
