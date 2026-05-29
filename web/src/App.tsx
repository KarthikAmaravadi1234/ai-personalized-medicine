import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Knowledge from "./pages/Knowledge";
import PatientDetail from "./pages/PatientDetail";
import Patients from "./pages/Patients";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/patient" element={<PatientDetail />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/knowledge" element={<Knowledge />} />
      </Routes>
    </Layout>
  );
}
