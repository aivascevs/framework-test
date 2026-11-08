// Test file for policy-config/semgrep/csharp.yaml (semgrep --test format).
using System.Data.SqlClient;
using System.Security.Cryptography;
class Repo {
  void Unsafe(string id, ILogger logger, string email) {
    // ruleid: csharp-sql-built-from-strings
    var cmd = new SqlCommand($"SELECT * FROM Users WHERE Id = {id}", conn);
    // ruleid: csharp-sql-built-from-strings
    var cmd2 = new SqlCommand("SELECT * FROM Users WHERE Id = " + id, conn);
    // ruleid: csharp-sql-built-from-strings
    var users = db.Users.FromSqlRaw($"SELECT * FROM Users WHERE Id = {id}");
    // ruleid: csharp-weak-hash
    var h = MD5.Create();
    // ruleid: csharp-certificate-validation-disabled
    handler.ServerCertificateCustomValidationCallback = (a, b, c, d) => true;
    // ruleid: csharp-hardcoded-credential
    string apiKey = "synthetic-not-a-real-key";
    // ruleid: csharp-personal-data-in-logs
    logger.LogInformation("User {Email} logged in", email);
  }
  void Safe(string id, ILogger logger, int userId) {
    // ok: csharp-sql-built-from-strings
    var cmd = new SqlCommand("SELECT * FROM Users WHERE Id = @id", conn);
    // ok: csharp-sql-built-from-strings
    var users = db.Users.FromSqlInterpolated($"SELECT * FROM Users WHERE Id = {id}");
    // ok: csharp-weak-hash
    var h = SHA256.Create();
    // ok: csharp-hardcoded-credential
    string label = "hello world";
    // ok: csharp-personal-data-in-logs
    logger.LogInformation("User {UserId} logged in", userId);
  }
}
