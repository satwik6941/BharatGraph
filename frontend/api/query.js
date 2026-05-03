// Vercel serverless proxy — keeps the Cloud Run URL and secret off the browser
export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const backendUrl = process.env.BACKEND_URL;
  const secret = process.env.API_SECRET_KEY;

  if (!backendUrl) {
    return res.status(500).json({ error: "BACKEND_URL not configured" });
  }

  try {
    const response = await fetch(`${backendUrl}/api/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(secret ? { "X-Secret-Key": secret } : {}),
      },
      body: JSON.stringify(req.body),
    });

    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (err) {
    return res.status(502).json({ error: `Backend unreachable: ${err.message}` });
  }
}