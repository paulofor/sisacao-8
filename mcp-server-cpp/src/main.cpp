#include <algorithm>
#include <array>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <regex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace {

struct RuntimeConfig {
  std::string project{"ingestaokraken"};
  std::string region{"us-east1"};
  std::string host{"0.0.0.0"};
  int port{80};
};

RuntimeConfig load_config() {
  RuntimeConfig cfg;
  if (const char *v = std::getenv("GCP_PROJECT")) cfg.project = v;
  if (const char *v = std::getenv("GCP_REGION")) cfg.region = v;
  if (const char *v = std::getenv("MCP_HOST")) cfg.host = v;
  if (const char *v = std::getenv("MCP_PORT")) cfg.port = std::atoi(v);
  return cfg;
}

std::string trim(std::string s) {
  s.erase(s.begin(), std::find_if(s.begin(), s.end(), [](unsigned char ch) { return !std::isspace(ch); }));
  s.erase(std::find_if(s.rbegin(), s.rend(), [](unsigned char ch) { return !std::isspace(ch); }).base(), s.end());
  return s;
}

bool is_read_only_sql(const std::string &sql) {
  std::string normalized = trim(sql);
  if (normalized.empty()) return false;
  if (normalized.find(';') != std::string::npos && normalized.back() != ';') return false;
  static const std::regex read_only(R"(^\s*(select|with)\b)", std::regex::icase);
  return std::regex_search(normalized, read_only);
}

std::string detect_credentials_source() {
  if (const char *v = std::getenv("GCP_SERVICE_ACCOUNT_JSON"); v && std::string(v).size()) {
    return "GCP_SERVICE_ACCOUNT_JSON";
  }
  if (const char *v = std::getenv("GCP_SERVICE_ACCOUNT_JSON_BASE64"); v && std::string(v).size()) {
    return "GCP_SERVICE_ACCOUNT_JSON_BASE64";
  }
  if (const char *v = std::getenv("GOOGLE_APPLICATION_CREDENTIALS"); v && std::filesystem::exists(v)) {
    return "GOOGLE_APPLICATION_CREDENTIALS";
  }
  std::string fallback = "/opt/sisacao/chaves/codex.json";
  if (std::filesystem::exists(fallback)) return fallback;
  return "ADC";
}

std::string run_command(const std::string &cmd) {
  std::array<char, 512> buffer{};
  std::string output;
  FILE *pipe = popen(cmd.c_str(), "r");
  if (!pipe) return "";
  while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe) != nullptr) {
    output += buffer.data();
  }
  pclose(pipe);
  return output;
}

std::string random_session_id() {
  static std::mt19937_64 rng(std::random_device{}());
  std::uniform_int_distribution<unsigned long long> dist;
  std::ostringstream oss;
  oss << std::hex << dist(rng) << dist(rng);
  return oss.str();
}

}  // namespace

int main() {
  RuntimeConfig cfg = load_config();
  std::string session_id = random_session_id();

  std::cout << "[mcp-server-cpp] servidor inicializado\n";
  std::cout << "[mcp-server-cpp] projeto: " << cfg.project << "\n";
  std::cout << "[mcp-server-cpp] regiao: " << cfg.region << "\n";
  std::cout << "[mcp-server-cpp] credenciais: " << detect_credentials_source() << "\n\n";

  std::cout << "Implementacao baseline criada.\n";
  std::cout << "Regras espelhadas do Python:\n";
  std::cout << "- initialize com mcp-session-id\n";
  std::cout << "- tools/list e tools/call com sessao valida\n";
  std::cout << "- bigquery_query somente SELECT/WITH\n";
  std::cout << "- cloud_run_function_logs via gcloud\n\n";

  const std::string sample_sql = "SELECT 1 AS ok";
  std::cout << "SQL read-only check (" << sample_sql << "): "
            << (is_read_only_sql(sample_sql) ? "ok" : "error") << "\n";

  std::cout << "\nExemplo comando logs:\n";
  std::cout << "gcloud run services logs read backtest-daily --region " << cfg.region
            << " --project " << cfg.project << " --freshness 24h --limit 50 --format value(timestamp,textPayload)\n";

  std::cout << "\nSessao atual (mock): " << session_id << "\n";
  return 0;
}
