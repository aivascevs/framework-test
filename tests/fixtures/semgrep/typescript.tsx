// Test file for policy-config/semgrep/typescript.yaml (semgrep --test format).
export function Unsafe({ html, userId, email, s }: any) {
  // ruleid: ts-sql-built-from-strings
  db.query("SELECT * FROM users WHERE id = " + userId);
  // ruleid: ts-sql-built-from-strings
  db.query(`SELECT * FROM users WHERE id = ${userId}`);
  // ruleid: ts-eval
  eval("1+1");
  // ruleid: ts-insecure-random
  const token = Math.random().toString(36);
  // ruleid: ts-hardcoded-credential
  const password = "synthetic-not-real";
  // ruleid: ts-personal-data-in-logs
  console.log("login", email);
  // ruleid: angular-bypass-security-trust
  s.bypassSecurityTrustHtml(html);
  // ruleid: react-dangerously-set-inner-html
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
export function Safe({ userId }: any) {
  // ok: ts-sql-built-from-strings
  db.query("SELECT * FROM users WHERE id = $1", [userId]);
  // ok: ts-insecure-random
  const id = crypto.randomUUID();
  // ok: ts-personal-data-in-logs
  console.log("login", userId);
  // ok: react-dangerously-set-inner-html
  return <div>{userId}</div>;
}
