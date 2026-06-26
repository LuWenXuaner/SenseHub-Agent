import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { LayoutProvider } from "@/context/LayoutContext";
import { LocaleProvider } from "@/context/LocaleContext";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { MimoConsoleShell } from "@/components/mimo/MimoConsoleShell";
import { MimoClawShell } from "@/components/mimo/MimoClawShell";
import { MimoCodeShell } from "@/components/mimo/MimoCodeShell";
import { CodePage } from "@/pages/CodePage";
import { MimoStudioShell } from "@/components/mimo/MimoStudioShell";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { LoginPage } from "@/pages/LoginPage";
import { HubPage } from "@/pages/HubPage";
import { HomePage } from "@/pages/HomePage";
import { StudioPage } from "@/pages/StudioPage";
import { ResearchPage } from "@/pages/ResearchPage";
import { ModelShowcasePage } from "@/pages/ModelShowcasePage";
import { UpdatesPage } from "@/pages/UpdatesPage";
import { UpdateDetailPage } from "@/pages/UpdateDetailPage";
import { TokenPlanPage } from "@/pages/TokenPlanPage";
import { ShareAchievementPage } from "@/pages/ShareAchievementPage";
import { ContactPage } from "@/pages/ContactPage";
import { ProductConsolePage } from "@/pages/ProductConsolePage";
import { ProductStudioPage } from "@/pages/ProductStudioPage";
import { ProductApiPage } from "@/pages/ProductApiPage";
import { TaskDetailPage } from "@/pages/TaskDetailPage";
import { CameraPage } from "@/pages/perception/CameraPage";
import { VoicePage } from "@/pages/perception/VoicePage";
import { ConsoleAccountPage } from "@/pages/console/ConsoleAccountPage";
import { ConsoleApiKeysPage } from "@/pages/console/ConsoleApiKeysPage";
import { ConsoleEngagementPage } from "@/pages/console/ConsoleEngagementPage";
import { ConsolePointsPage } from "@/pages/console/ConsolePointsPage";
import { ConsoleTokenPlanPage } from "@/pages/console/ConsoleTokenPlanPage";
import { ConsoleBillsPage } from "@/pages/console/ConsoleBillsPage";
import { ConsolePluginsPage } from "@/pages/console/ConsolePluginsPage";
import { ConsoleSecurityPage } from "@/pages/console/ConsoleSecurityPage";
import { ConsoleInvitePage } from "@/pages/console/ConsoleInvitePage";
import {
  ConsoleExchangeLogPage,
  ConsolePointsHistoryPage,
} from "@/pages/console/ConsolePointsHistoryPage";
import { ConsoleAdminUsersPage } from "@/pages/console/ConsoleAdminUsersPage";
import {
  CookiePolicyPage,
  PrivacyPolicyPage,
  TermsPage,
} from "@/pages/legal/LegalPages";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const location = useLocation();
  if (!token) {
    const redirect = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?redirect=${encodeURIComponent(redirect)}`} replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="product/api" element={<ProductApiPage />} />
      <Route element={<MarketingLayout />}>
        <Route index element={<HomePage />} />
        <Route path="research" element={<ResearchPage />} />
        <Route path="models" element={<ModelShowcasePage />} />
        <Route path="updates" element={<UpdatesPage />} />
        <Route path="updates/:slug" element={<UpdateDetailPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="share/achievement/:token" element={<ShareAchievementPage />} />
        <Route path="token-plan" element={<TokenPlanPage />} />
        <Route path="billing" element={<Navigate to="/token-plan" replace />} />
        <Route path="legal/privacy" element={<PrivacyPolicyPage />} />
        <Route path="legal/terms" element={<TermsPage />} />
        <Route path="legal/cookies" element={<CookiePolicyPage />} />
        <Route path="product/console" element={<ProductConsolePage />} />
        <Route path="product/studio" element={<ProductStudioPage />} />
      </Route>
      <Route
        element={
          <PrivateRoute>
            <MimoConsoleShell />
          </PrivateRoute>
        }
      >
        <Route path="console">
          <Route index element={<Navigate to="/console/account" replace />} />
          <Route path="account" element={<ConsoleAccountPage />} />
          <Route path="api-keys" element={<ConsoleApiKeysPage />} />
          <Route path="points" element={<ConsolePointsPage />} />
          <Route path="engagement" element={<ConsoleEngagementPage />} />
          <Route path="balance" element={<Navigate to="/console/points" replace />} />
          <Route path="token-plan" element={<ConsoleTokenPlanPage />} />
          <Route path="bills" element={<ConsoleBillsPage />} />
          <Route path="points-history" element={<ConsolePointsHistoryPage />} />
          <Route path="recharge" element={<Navigate to="/console/points-history" replace />} />
          <Route path="exchange" element={<ConsoleExchangeLogPage />} />
          <Route path="invoice" element={<Navigate to="/console/exchange" replace />} />
          <Route path="invite" element={<ConsoleInvitePage />} />
          <Route path="plugins" element={<ConsolePluginsPage />} />
          <Route path="security" element={<ConsoleSecurityPage />} />
          <Route path="admin/users" element={<ConsoleAdminUsersPage />} />
        </Route>
      </Route>
      <Route
        element={
          <PrivateRoute>
            <MimoClawShell />
          </PrivateRoute>
        }
      >
        <Route path="claw" element={<HubPage />} />
      </Route>
      <Route
        element={
          <PrivateRoute>
            <MimoCodeShell />
          </PrivateRoute>
        }
      >
        <Route path="code" element={<CodePage />} />
      </Route>
      <Route
        element={
          <PrivateRoute>
            <MimoStudioShell />
          </PrivateRoute>
        }
      >
        <Route path="studio" element={<StudioPage />} />
      </Route>
      <Route
        path="perception/virtual-screen"
        element={
          <PrivateRoute>
            <Navigate to="/claw?calibrate=virtual" replace />
          </PrivateRoute>
        }
      />
      <Route
        element={
          <PrivateRoute>
            <WorkspaceShell />
          </PrivateRoute>
        }
      >
        <Route path="dashboard" element={<Navigate to="/claw" replace />} />
        <Route path="command" element={<Navigate to="/claw" replace />} />
        <Route path="tasks" element={<Navigate to="/claw" replace />} />
        <Route path="tasks/:id" element={<TaskDetailPage />} />
        <Route path="settings" element={<Navigate to="/console/api-keys" replace />} />
        <Route path="perception/camera" element={<CameraPage />} />
        <Route path="perception/voice" element={<VoicePage />} />
        <Route path="perception" element={<Navigate to="/perception/camera" replace />} />
        <Route path="rules" element={<Navigate to="/console/plugins" replace />} />
        <Route path="system/models" element={<Navigate to="/models" replace />} />
        <Route path="system/security" element={<Navigate to="/console/security" replace />} />
        <Route path="system/settings" element={<Navigate to="/console/api-keys" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <LocaleProvider>
      <AuthProvider>
        <LayoutProvider>
          <AppRoutes />
        </LayoutProvider>
      </AuthProvider>
    </LocaleProvider>
  );
}
