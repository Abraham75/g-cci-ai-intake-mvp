import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const authority = import.meta.env.VITE_GCCI_OIDC_AUTHORITY || "";
const clientId = import.meta.env.VITE_GCCI_OIDC_CLIENT_ID || "";
const redirectUri = import.meta.env.VITE_GCCI_OIDC_REDIRECT_URI || `${window.location.origin}${window.location.pathname}`;
const postLogoutRedirectUri = import.meta.env.VITE_GCCI_OIDC_POST_LOGOUT_REDIRECT_URI || window.location.origin;
const scope = import.meta.env.VITE_GCCI_OIDC_SCOPE || "openid profile email";

export const oidcConfigured = Boolean(authority && clientId);

const manager = oidcConfigured
  ? new UserManager({
      authority,
      client_id: clientId,
      redirect_uri: redirectUri,
      post_logout_redirect_uri: postLogoutRedirectUri,
      response_type: "code",
      scope,
      automaticSilentRenew: true,
      loadUserInfo: true,
      userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    })
  : null;

let callbackHandled = false;

export async function initializeAuth() {
  if (!manager) return null;
  if (!callbackHandled && window.location.search.includes("code=") && window.location.search.includes("state=")) {
    callbackHandled = true;
    const user = await manager.signinRedirectCallback();
    window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
    return user;
  }
  return manager.getUser();
}

export async function getAccessToken() {
  if (!manager) {
    // Development-only escape hatch. Never compile a production token into the Vite bundle.
    return import.meta.env.DEV ? window.sessionStorage.getItem("gcci-dev-access-token") : null;
  }
  const user = await manager.getUser();
  if (!user || user.expired) return null;
  return user.access_token;
}

export async function signIn() {
  if (!manager) throw new Error("OIDC is not configured for this frontend");
  await manager.signinRedirect();
}

export async function signOut() {
  if (!manager) return;
  await manager.signoutRedirect();
}

export function subscribeAuth(listener) {
  if (!manager) return () => {};
  const onLoaded = (user) => listener(user);
  const onUnloaded = () => listener(null);
  const onExpired = () => listener(null);
  manager.events.addUserLoaded(onLoaded);
  manager.events.addUserUnloaded(onUnloaded);
  manager.events.addAccessTokenExpired(onExpired);
  return () => {
    manager.events.removeUserLoaded(onLoaded);
    manager.events.removeUserUnloaded(onUnloaded);
    manager.events.removeAccessTokenExpired(onExpired);
  };
}
