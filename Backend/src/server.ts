import "dotenv/config";
import app from "./app";

const PORT = parseInt(process.env.PORT || "3001", 10);

app.listen(PORT, () => {
  console.log(`\n🚀 Gotham GNN Investigator API`);
  console.log(`   Listening on http://localhost:${PORT}`);
  console.log(`   Health:      http://localhost:${PORT}/health`);
  console.log(`   FIR Query:   POST http://localhost:${PORT}/api/fir/query`);
  console.log(`   Gang Eval:   POST http://localhost:${PORT}/api/fir/gang`);
  console.log(`\n   X-API-Key required for all /api/* routes.`);
  console.log(`   Current key: ${process.env.API_KEY?.slice(0, 8)}...`);
});
