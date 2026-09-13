import { NextFunction, Request, Response } from "express";
import { timingSafeEqual } from "crypto";

interface Identity {
  role: string;
  name: string;
}

function safeEqual(a: string, b: string): boolean {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

function configuredTokens(): Record<string, string> {
  const raw = process.env.GCCI_API_TOKENS || "{}";
  try {
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : {};
  } catch {
    return {};
  }
}

export function apiAuth(req: Request, res: Response, next: NextFunction) {
  if (process.env.NODE_ENV !== "production") return next();
  if (req.path === "/health/live" || req.path === "/api/scoring/score") return next();

  const header = req.header("authorization") || "";
  if (!header.toLowerCase().startsWith("bearer ")) {
    return res.status(401).json({ error: "bearer_token_required" });
  }
  const supplied = header.slice(7).trim();
  const tokens = configuredTokens();
  for (const [token, identityString] of Object.entries(tokens)) {
    if (!safeEqual(supplied, token)) continue;
    const [role, name] = String(identityString).split(":", 2);
    if (!role || !name) return res.status(500).json({ error: "invalid_auth_configuration" });
    (res.locals as { actor?: Identity }).actor = { role: role.toUpperCase(), name };
    return next();
  }
  return res.status(401).json({ error: "invalid_bearer_token" });
}
