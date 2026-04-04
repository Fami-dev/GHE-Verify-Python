"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Ban, Clock, Terminal } from "lucide-react";

type StatusType = "pending" | "approved" | "rejected" | "timeout" | "awaiting_confirm" | "cancelled" | "precheck_failed" | "session_expired" | "none";
type VerifyType = "student" | "teacher";

interface Task {
  id: string;
  status: StatusType;
  started_at: number;
  telegram_user_id?: string | number;
  github_username?: string;
  indicator?: string;
  polling_active?: boolean;
}

const INDICATOR_CAPACITY = 100;
const INDICATOR_ROWS = 5;
const INDICATOR_COLUMNS = INDICATOR_CAPACITY / INDICATOR_ROWS;

interface ProfileCheck {
  github_username?: string;
  email?: string;
  has_2fa?: boolean;
  age_days?: number;
  criteria_ok?: boolean;
}

interface UserStats {
  credits: number | string;
  invites: number;
  loaded: boolean;
  isOwner: boolean;
  isBanned: boolean;
  banReason: string;
  maintenanceMode: boolean;
  dailyLimitDisplay: string;
  studentEnabled: boolean;
  teacherEnabled: boolean;
  studentCost: number;
  teacherCost: number;
  groupsJoined?: boolean;
  mathSolved?: boolean;
}

const DEFAULT_USER_STATS: UserStats = {
  credits: 0,
  invites: 0,
  loaded: false,
  isOwner: false,
  isBanned: false,
  banReason: "",
  maintenanceMode: false,
  dailyLimitDisplay: "0 / Unlimited",
  studentEnabled: true,
  teacherEnabled: true,
  studentCost: 1,
  teacherCost: 1,
  groupsJoined: true,
  mathSolved: true,
};

const emptyCell = (index: number): Task => ({
  id: `empty-${index}`,
  status: "none",
  started_at: 0,
});

function mapTasksToGrid(tasks: Task[]): Task[] {
  const arranged: Task[] = Array.from({ length: INDICATOR_CAPACITY }, (_, i) => emptyCell(i));
  const latest = tasks.slice(0, INDICATOR_CAPACITY).reverse();

  for (let i = 0; i < latest.length; i += 1) {
    const row = i % INDICATOR_ROWS;
    const col = Math.floor(i / INDICATOR_ROWS);
    const gridIndex = row * INDICATOR_COLUMNS + col;
    arranged[gridIndex] = latest[i] || emptyCell(i);
  }

  return arranged;
}

export default function Home() {
  type TelegramUser = {
    id: number;
    username?: string;
    first_name?: string;
  };

  const [telegramUser, setTelegramUser] = useState<TelegramUser | null>(null);
  const [cookieInput, setCookieInput] = useState("");
  const [verifyType, setVerifyType] = useState<VerifyType>("student");
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>("");
  const [schools, setSchools] = useState<Array<{ id: string | number; name: string; type: string }>>([]);
  const [loadingSchools, setLoadingSchools] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState({
    success_rate: 0,
    total_processed: 0,
    queue_active: 0,
    queue_limit: 2,
  });
  const [userStats, setUserStats] = useState<UserStats>(DEFAULT_USER_STATS);
  const [isTMA, setIsTMA] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);

  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeGithubName, setActiveGithubName] = useState<string>("Waiting...");
  const [activeGithubRaw, setActiveGithubRaw] = useState<string>("-");
  const [activeGithubEmail, setActiveGithubEmail] = useState<string>("-");
  const [activeProfile, setActiveProfile] = useState<ProfileCheck | null>(null);
  const [activeLogs, setActiveLogs] = useState<string[]>([]);
  const [activeIndicator, setActiveIndicator] = useState<string>("-");
  const [taskStatus, setTaskStatus] = useState<StatusType>("none");
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);

  const canUseStudentMode = userStats.isOwner || userStats.studentEnabled;
  const canUseTeacherMode = userStats.isOwner || userStats.teacherEnabled;
  const selectedTypeEnabled =
    verifyType === "student" ? canUseStudentMode : canUseTeacherMode;
  const anyTypeEnabled = canUseStudentMode || canUseTeacherMode;
  const selectedModeOwnerOnly = userStats.isOwner && (
    (verifyType === "student" && !userStats.studentEnabled)
    || (verifyType === "teacher" && !userStats.teacherEnabled)
  );
  const isBanBlocked = userStats.loaded && !userStats.isOwner && userStats.isBanned;
  const isMaintenanceBlocked = userStats.loaded && !userStats.isOwner && userStats.maintenanceMode;
  const selectedTypeCost = verifyType === "student" ? userStats.studentCost : userStats.teacherCost;
  const numericCredits = typeof userStats.credits === "number" ? userStats.credits : Number.NaN;
  const hasEnoughCredits = userStats.isOwner || Number.isNaN(numericCredits) || numericCredits >= selectedTypeCost;

  const loadUserStats = async (userId: number | string) => {
    const res = await fetch(`/api/user/${userId}`);
    const data = await res.json();

    if (!(data.success && data.data)) {
      setUserStats((prev) => ({ ...prev, loaded: true }));
      return;
    }

    const userData = data.data;
    const verify = userData.verify || {};

    const nextStats: UserStats = {
      credits: userData.credits ?? 0,
      invites: Number(userData.total_invites ?? 0),
      loaded: true,
      isOwner: Boolean(userData.is_owner),
      isBanned: Boolean(userData.is_banned),
      banReason: String(userData.ban_reason ?? ""),
      maintenanceMode: Boolean(verify.maintenance_mode),
      dailyLimitDisplay: userData.daily_limit?.display ?? "0 / Unlimited",
      studentEnabled: verify.student_enabled !== false,
      teacherEnabled: verify.teacher_enabled !== false,
      studentCost: Number(verify.student_credit_cost ?? 1),
      teacherCost: Number(verify.teacher_credit_cost ?? 1),
      groupsJoined: Boolean(userData.groups_joined),
      mathSolved: Boolean(userData.math_solved),
    };

    setUserStats(nextStats);

    if (!nextStats.isOwner) {
      if (!nextStats.studentEnabled && nextStats.teacherEnabled) {
        setVerifyType("teacher");
      }
      if (!nextStats.teacherEnabled && nextStats.studentEnabled) {
        setVerifyType("student");
      }
    }
  };

  const loadSchools = useCallback(async () => {
    if (!telegramUser || !userStats.isOwner) return;
    
    setLoadingSchools(true);
    try {
      const res = await fetch(
        `/api/schools?type=${verifyType}&telegram_user_id=${telegramUser.id}`
      );
      
      if (res.ok) {
        const data = await res.json();
        setSchools(data.schools || []);
      } else {
        setSchools([]);
      }
    } catch (error) {
      console.error("Failed to load schools:", error);
      setSchools([]);
    } finally {
      setLoadingSchools(false);
    }
  }, [telegramUser, userStats.isOwner, verifyType]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const tg = (window as typeof window & { Telegram?: { WebApp?: { initDataUnsafe?: { user?: TelegramUser }; ready: () => void; close: () => void } } }).Telegram?.WebApp;
      if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        tg.ready();
        const user = tg.initDataUnsafe.user;
        setTelegramUser(user);
        setIsTMA(true);

        loadUserStats(user.id).catch(() =>
          setUserStats((prev) => ({ ...prev, loaded: true })),
        );
      } else {
        setAccessDenied(true);
      }
    }
  }, []);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const data = await res.json();
          if (data.success) {
            setTasks(data.tasks);
            setStats(data.stats);
          }
        }
      } catch (e) {
        console.error("Failed to load queue status:", e);
      }
    };

    if (!accessDenied && !isMaintenanceBlocked && !isBanBlocked) {
      fetchStatus();
      const interval = setInterval(fetchStatus, 3000);
      return () => clearInterval(interval);
    }
  }, [accessDenied, isMaintenanceBlocked, isBanBlocked]);

  useEffect(() => {
    if (userStats.isOwner && telegramUser) {
      loadSchools();
      setSelectedSchoolId(""); // Reset selection ketika type berubah
    }
  }, [verifyType, userStats.isOwner, telegramUser, loadSchools]);

  useEffect(() => {
    if (
      !activeTaskId
      || taskStatus === "approved"
      || taskStatus === "rejected"
      || taskStatus === "cancelled"
      || taskStatus === "precheck_failed"
      || taskStatus === "session_expired"
    ) {
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const res = await fetch(`/api/logs/${activeTaskId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.success) {
            setActiveLogs(data.logs || []);
            if (data.github_username) {
              setActiveGithubName(data.github_username);
            }
            if (typeof data.github_username_raw === "string") {
              setActiveGithubRaw(data.github_username_raw || "-");
            }
            if (typeof data.github_email === "string") {
              setActiveGithubEmail(data.github_email || "-");
            }
            if (data.profile) {
              setActiveProfile(data.profile);
            }
            if (typeof data.indicator === "string") {
              setActiveIndicator(data.indicator);
            }
            if (data.status !== "pending") {
              setTaskStatus(data.status);
              setIsLoading(false);
              if (telegramUser?.id) {
                loadUserStats(telegramUser.id).catch(() => null);
              }
            }
          }
        }
      } catch {
        console.error("Error fetching logs");
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [activeTaskId, taskStatus, telegramUser]);

  useEffect(() => {
    if (!telegramUser?.id || accessDenied) return;

    const intervalId = setInterval(() => {
      loadUserStats(telegramUser.id).catch(() => null);
    }, 8000);

    return () => clearInterval(intervalId);
  }, [telegramUser, accessDenied]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cookieInput.trim()) return;

    if (isMaintenanceBlocked) {
      alert("Verification is currently under maintenance. Please try again later.");
      return;
    }

    if (isBanBlocked) {
      alert("Your account is blocked from using this website.");
      return;
    }

    if (!anyTypeEnabled) {
      alert("Verification is currently disabled by owner.");
      return;
    }

    if (!selectedTypeEnabled) {
      alert("Selected verification type is disabled by owner.");
      return;
    }

    if (!hasEnoughCredits) {
      alert(`Insufficient credits. You need ${selectedTypeCost} credits for this verification type.`);
      return;
    }

    if (stats.queue_active >= stats.queue_limit) {
      alert(`Queue is full (${stats.queue_active}/${stats.queue_limit}). Please wait and try again.`);
      return;
    }

    if (!isTMA && telegramUser?.id === 1234) {
      alert("Please open this app inside Telegram!");
      return;
    }

    setIsLoading(true);
    setActiveLogs(["Opening connection to server..."]);
    setActiveIndicator("Sending verification request...");
    setTaskStatus("pending");
    
    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cookies: cookieInput,
          telegram_user_id: telegramUser?.id,
          telegram_username: telegramUser?.username,
          verify_type: verifyType,
          school_id: selectedSchoolId || undefined, // Send school_id jika ada
        }),
      });
      const data = await res.json();
      if (data.success) {
        setCookieInput("");
        setActiveTaskId(data.task_id);
        setActiveGithubName("Waiting...");
        setActiveGithubRaw("-");
        setActiveGithubEmail("-");
        setActiveProfile(null);
        setActiveIndicator("Waiting for server response...");
      } else {
        setActiveLogs((prev) => [...prev, `[ERROR] ${data.error}`]);
        setTaskStatus("rejected");
        setIsLoading(false);
        alert("Error: " + data.error);
      }
    } catch (e) {
      console.error(e);
      setActiveLogs((prev) => [...prev, "[ERROR] Network Error connecting to server."]);
      setTaskStatus("rejected");
      setIsLoading(false);
    }
  };

  const handleContinue = async () => {
    if (!activeTaskId) return;
    setIsLoading(true);
    setTaskStatus("pending");
    setActiveIndicator("Continuing verification process...");

    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "continue", task_id: activeTaskId }),
      });
      const data = await res.json();
      if (!data.success) {
        setIsLoading(false);
        setTaskStatus("awaiting_confirm");
        setActiveIndicator("Failed to continue verification process.");
        setActiveLogs((prev) => [...prev, `[ERROR] ${data.error || "Failed to continue"}`]);
      }
    } catch {
      setIsLoading(false);
      setTaskStatus("awaiting_confirm");
      setActiveIndicator("Network error while continuing.");
      setActiveLogs((prev) => [...prev, "[ERROR] Network error while continuing verification."]);
    }
  };

  const handleCancel = async () => {
    if (!activeTaskId) return;

    const cancelBeforeSubmit = taskStatus === "awaiting_confirm";
    const confirmMessage = cancelBeforeSubmit
      ? "Are you sure you want to cancel? Credits will not be charged because verification has not been continued yet."
      : "Are you sure you want to stop this task? Credits will NOT be refunded.";

    const confirmed = window.confirm(confirmMessage);
    if (!confirmed) return;

    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "cancel", task_id: activeTaskId }),
      });
      const data = await res.json();
      if (data.success) {
        const creditCharged = Boolean(data.credit_charged);
        setTaskStatus("cancelled");
        setIsLoading(false);
        if (!creditCharged) {
          setActiveIndicator("Verification cancelled before continue. Credits were not charged.");
          setActiveLogs((prev) => [...prev, "[INFO] Verification cancelled before continue. Credits were not charged."]);
        } else {
          setActiveIndicator("Verification cancelled. Credits are not refunded.");
          setActiveLogs((prev) => [...prev, "[INFO] Verification cancelled by user. Credits are not refunded."]);
        }
      } else {
        setActiveLogs((prev) => [...prev, `[ERROR] ${data.error || "Failed to cancel"}`]);
      }
    } catch {
      setActiveIndicator("Network error while canceling.");
      setActiveLogs((prev) => [...prev, "[ERROR] Network error while canceling verification."]);
    }
  };

  const handleResendCookies = async () => {
    if (!activeTaskId || !cookieInput.trim()) {
      alert("Please paste fresh cookies first.");
      return;
    }

    setIsLoading(true);
    setTaskStatus("pending");
    setActiveIndicator("Resending cookies and resuming poller...");

    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "resend_cookies",
          task_id: activeTaskId,
          cookies: cookieInput,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setCookieInput("");
        setActiveLogs((prev) => [...prev, "[ACTION] New cookies submitted. Poller resumed."]);
      } else {
        setTaskStatus("session_expired");
        setIsLoading(false);
        setActiveLogs((prev) => [...prev, `[ERROR] ${data.error || "Failed to resend cookies"}`]);
        setActiveIndicator("Failed to resume poller with new cookies.");
      }
    } catch {
      setTaskStatus("session_expired");
      setIsLoading(false);
      setActiveLogs((prev) => [...prev, "[ERROR] Network error while resending cookies."]);
      setActiveIndicator("Network error while resending cookies.");
    }
  };

  const getGridColor = (status: StatusType) => {
    switch (status) {
      case "approved": return "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]";
      case "rejected": return "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]";
      case "pending": return "bg-white animate-pulse shadow-[0_0_10px_rgba(255,255,255,0.5)]";
      case "timeout": return "bg-black border border-gray-500 shadow-[0_0_10px_rgba(0,0,0,0.75)]";
      case "awaiting_confirm": return "bg-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.45)]";
      case "cancelled": return "bg-slate-500 shadow-[0_0_10px_rgba(100,116,139,0.45)]";
      case "session_expired": return "bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.45)]";
      default: return "bg-[#1a1a1a]"; 
    }
  };

  const gridCells = mapTasksToGrid(tasks);

  if (accessDenied) {
    return (
      <div className="min-h-screen bg-[#290b3b] text-white flex flex-col items-center justify-center p-4">
        <Activity className="w-16 h-16 text-indigo-500 mb-6" />
        <h1 className="text-3xl font-black mb-2 text-center">Access Denied</h1> 
        <p className="text-gray-300 text-center max-w-sm mb-8">
          This WebApp must be launched directly from the Telegram Bot to detect your account and credits.
        </p>
        <a
          href="https://t.me/GHSVerify_bot"
          target="_blank"
          rel="noopener noreferrer"
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-xl transition-all shadow-lg"
        >
          Open @GHSVerify_bot
        </a>
      </div>
    );
  }

  if (isTMA && isMaintenanceBlocked) {
    return (
      <div className="min-h-screen bg-[#290b3b] text-white flex flex-col items-center justify-center p-4">
        <Activity className="w-16 h-16 text-amber-400 mb-6" />
        <h1 className="text-3xl font-black mb-3 text-center">Maintenance Mode</h1>
        <div className="bg-[#1a0624] p-6 rounded-2xl w-full max-w-sm border border-amber-700/40">
          <p className="text-amber-100 text-sm leading-relaxed text-center">
            Web verify sedang maintenance. Selama maintenance aktif, user tidak bisa mengakses verifikasi.
          </p>
          <p className="text-amber-300/90 text-xs mt-4 text-center">
            Silakan tunggu dan coba lagi nanti atau hubungi owner bot.
          </p>
        </div>
        <button
          onClick={() => {
            const tg = (window as typeof window & { Telegram?: { WebApp?: { close: () => void } } }).Telegram?.WebApp;
            if (tg) tg.close();
          }}
          className="mt-8 bg-amber-600 hover:bg-amber-700 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg"
        >
          Return to Bot
        </button>
      </div>
    );
  }

  if (isTMA && isBanBlocked) {
    return (
      <div className="min-h-screen bg-[#290b3b] text-white flex flex-col items-center justify-center p-4">
        <Ban className="w-16 h-16 text-red-500 mb-6" />
        <h1 className="text-3xl font-black mb-3 text-center">Access Blocked</h1>
        <div className="bg-[#1a0624] p-6 rounded-2xl w-full max-w-sm border border-red-700/40">
          <p className="text-red-100 text-sm leading-relaxed text-center">
            Your account is blocked from using this website.
          </p>
          <p className="text-red-200 text-sm leading-relaxed text-center mt-3">
            Reason: {userStats.banReason?.trim() || "Violation of terms"}
          </p>
          <p className="text-red-300/90 text-xs mt-4 text-center">
            Contact <a href="https://t.me/arcvour" target="_blank" rel="noopener noreferrer" className="underline font-semibold">@arcvour</a> to appeal.
          </p>
        </div>
        <button
          onClick={() => {
            const tg = (window as typeof window & { Telegram?: { WebApp?: { close: () => void } } }).Telegram?.WebApp;
            if (tg) tg.close();
          }}
          className="mt-8 bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg"
        >
          Return to Bot
        </button>
      </div>
    );
  }

  if (isTMA && userStats.loaded && (!userStats.groupsJoined || !userStats.mathSolved)) {
    return (
      <div className="min-h-screen bg-[#290b3b] text-white flex flex-col items-center justify-center p-4">
        <Activity className="w-16 h-16 text-red-500 mb-6" />
        <h1 className="text-3xl font-black mb-4 text-center">Verification Required</h1>
        <div className="bg-[#1a0624] p-6 rounded-2xl w-full max-w-sm border border-rose-900/30">
          <p className="text-gray-300 text-sm mb-6 text-center">
            You must complete the following requirements in the bot before using this Mini App:
          </p>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <div className={`w-6 h-6 rounded-md flex items-center justify-center ${userStats.mathSolved ? 'bg-green-500' : 'bg-red-500'}`}>
                {userStats.mathSolved ? "✓" : "✗"}
              </div>
              <span className="text-sm font-medium">Complete Security Math Captcha</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className={`w-6 h-6 rounded-md flex items-center justify-center ${userStats.groupsJoined ? 'bg-green-500' : 'bg-red-500'}`}>
                {userStats.groupsJoined ? "✓" : "✗"}
              </div>
              <span className="text-sm font-medium">Join all required Telegram Channels</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => {
            const tg = (window as typeof window & { Telegram?: { WebApp?: { close: () => void } } }).Telegram?.WebApp;
            if (tg) tg.close();
          }}
          className="mt-8 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-xl transition-all shadow-lg"
        >
          Return to Bot
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#290b3b] text-white p-4 md:p-8 font-sans" onClick={() => setSelectedCellId(null)}>
      <div className="max-w-xl mx-auto space-y-8 mt-10">
        
        <div className="bg-[#1a0628] p-6 rounded-2xl border border-purple-900/50 flex flex-col shadow-2xl">
          <div className="flex items-center justify-between w-full mb-4">       
            <div>
              <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">GHS Web Verify</h1> 
              <p className="text-purple-300 mt-1 text-sm">
                User: <span className="text-white font-medium">@{telegramUser?.username || telegramUser?.first_name || "Guest"}</span>
                <span className="ml-2 text-xs text-purple-400/70">({telegramUser?.id || "-"})</span>
              </p>
            </div>
            <Activity className="w-8 h-8 text-indigo-400" />
          </div>

          <div className="grid grid-cols-2 gap-3 mt-2 border-t border-purple-900/50 pt-4">
            <div className="bg-[#14041f] rounded-lg p-3 border border-purple-900/30">
              <p className="text-purple-300 text-xs font-semibold">💳 Credits</p>
              <p className="text-lg font-bold text-blue-400">
                {!userStats.loaded ? "..." : userStats.credits} <span className="text-xs text-purple-400 font-normal">balance</span>
              </p>
            </div>
            <div className="bg-[#14041f] rounded-lg p-3 border border-purple-900/30">
              <p className="text-purple-300 text-xs font-semibold">👥 Invites</p>
              <p className="text-lg font-bold text-purple-400">
                {!userStats.loaded ? "..." : userStats.invites} <span className="text-xs text-purple-400 font-normal">users</span>
              </p>
            </div>
            <div className="bg-[#14041f] rounded-lg p-3 border border-purple-900/30">
              <p className="text-purple-300 text-xs font-semibold">⏱ Daily Limit</p>
              <p className="text-sm font-bold text-white">
                {!userStats.loaded ? "..." : userStats.dailyLimitDisplay}
              </p>
            </div>
            <div className="bg-[#14041f] rounded-lg p-3 border border-purple-900/30">
              <p className="text-purple-300 text-xs font-semibold">🎫 Verify Cost</p>
              <p className="text-sm font-bold text-indigo-300">
                S {userStats.studentCost} | T {userStats.teacherCost}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-[#1a0628] p-4 rounded-xl border border-purple-900/50 text-center shadow-xl">
            <h3 className="text-purple-300 text-xs font-semibold uppercase tracking-wider">Success Rate</h3>
            <p className="text-3xl font-black text-green-400 mt-1">{stats.success_rate}%</p>
          </div>
          <div className="bg-[#1a0628] p-4 rounded-xl border border-purple-900/50 text-center shadow-xl">
            <h3 className="text-purple-300 text-xs font-semibold uppercase tracking-wider">Total Processed</h3>
            <p className="text-3xl font-black text-white mt-1">{stats.total_processed}</p>
          </div>
        </div>

        <div className="bg-[#1a0628] p-6 rounded-2xl border border-purple-900/50 shadow-xl overflow-visible">
          <h2 className="text-sm font-semibold text-purple-300 mb-6 flex items-center gap-2">
            <Clock className="w-4 h-4" /> Live Verification Queue ({stats.queue_active}/{stats.queue_limit})
          </h2>
          <div className="rounded-xl overflow-visible" onClick={() => setSelectedCellId(null)}>
            <div
              className="relative grid gap-1 place-items-center bg-black/40 p-3 border border-purple-900/50 rounded-xl overflow-visible"
              style={{ gridTemplateColumns: `repeat(${INDICATOR_COLUMNS}, minmax(0, 1fr))` }}
            >
              {gridCells.map((cell, idx) => (
                <div
                  key={idx}
                  className="relative w-full flex justify-center"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (cell.status === "none") return;
                    setSelectedCellId((prev) => (prev === cell.id ? null : cell.id));
                  }}
                >
                  <div
                    className={`w-full max-w-[12px] md:max-w-[14px] aspect-square rounded-[2px] transition-all duration-500 cursor-pointer ${getGridColor(cell.status)}`}
                  />
                  {cell.status !== "none" && selectedCellId === cell.id && (
                    <div
                      className="absolute z-[9999] top-full sm:top-auto sm:bottom-full left-0 sm:left-1/2 sm:-translate-x-1/2 mt-2 sm:mt-0 sm:mb-2 bg-[#000000] p-2 sm:p-3 rounded-lg text-[10px] sm:text-xs leading-relaxed text-white border border-gray-700 shadow-2xl opacity-100 w-44 sm:w-56 max-w-[calc(100vw-1.25rem)] whitespace-normal break-words"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <p className="font-bold text-indigo-400 mb-1 border-b border-gray-700 pb-1">Task Info</p>
                      <p><span className="text-gray-400">TG ID:</span> {cell.telegram_user_id || "Unknown"}</p>
                      <p><span className="text-gray-400">GH User:</span> {cell.github_username || "Waiting..."}</p>
                      <p><span className="text-gray-400">Time:</span> {cell.started_at ? new Date(cell.started_at * 1000).toLocaleTimeString() : "-"}</p>
                      <p><span className="text-gray-400">Status:</span> <span className="uppercase">{cell.status}</span></p>
                      <p><span className="text-gray-400">Indicator:</span> {cell.indicator || "-"}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-4 mt-6 text-xs text-purple-300 justify-center font-medium">
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-green-500 rounded-sm"></div> Approved</span>
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-red-500 rounded-sm"></div> Rejected</span>
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-white rounded-sm"></div> Pending</span>
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-amber-500 rounded-sm"></div> Session expired</span>
            <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-black border border-gray-500 rounded-sm"></div> No info</span>
          </div>
        </div>

        <div className="bg-[#1a0628] p-6 rounded-2xl border border-purple-900/50 shadow-xl">
          <h2 className="text-lg font-bold mb-4">Submit Session</h2>

          {!anyTypeEnabled && (
            <div className="mb-4 rounded-xl border border-red-700/40 bg-red-950/40 p-3 text-sm text-red-300">
              Verification is temporarily disabled by owner.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex bg-[#12031c] rounded-xl p-1 border border-purple-900/50">
              {canUseStudentMode && (
                <button
                  type="button"
                  onClick={() => setVerifyType("student")}
                  className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                    verifyType === "student" ? "bg-indigo-500 text-white shadow-md" : "text-purple-400 hover:text-white"
                  }`}
                >
                  Student ({userStats.studentCost} cr)
                </button>
              )}
              {canUseTeacherMode && (
                <button
                  type="button"
                  onClick={() => setVerifyType("teacher")}
                  className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                    verifyType === "teacher" ? "bg-indigo-500 text-white shadow-md" : "text-purple-400 hover:text-white"
                  }`}
                >
                  Teacher ({userStats.teacherCost} cr)
                </button>
              )}
            </div>
            {selectedModeOwnerOnly && (
              <div className="rounded-xl border border-indigo-700/40 bg-indigo-950/30 p-3 text-xs text-indigo-200">
                Mode ini sedang OFF untuk publik. Hanya owner yang bisa menggunakan mode ini.
              </div>
            )}
            {!hasEnoughCredits && (
              <div className="rounded-xl border border-amber-700/40 bg-amber-950/30 p-3 text-sm text-amber-300">
                Credit not enough. Required: {selectedTypeCost} credits for {verifyType} verification.
              </div>
            )}
            
            {/* School Selector untuk Owner */}
            {userStats.isOwner && (
              <div>
                <label className="block text-sm font-medium text-purple-300 mb-2">
                  Select School {loadingSchools && <span className="text-xs text-gray-500">(Loading...)</span>}
                </label>
                <select
                  value={selectedSchoolId}
                  onChange={(e) => setSelectedSchoolId(e.target.value)}
                  className="w-full bg-black/60 border border-purple-900/50 rounded-xl p-3 text-sm text-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all"
                  disabled={loadingSchools || !anyTypeEnabled}
                >
                  <option value="">🎲 Random School (Default)</option>
                  {schools.map((school) => (
                    <option key={school.id} value={school.id}>
                      {school.name}
                    </option>
                  ))}
                </select>
                {selectedSchoolId && (
                  <p className="mt-1.5 text-xs text-indigo-400">
                    ✓ Selected school will be used for this verification
                  </p>
                )}
              </div>
            )}
            
            <div>
              <textarea
                value={cookieInput}
                onChange={(e) => setCookieInput(e.target.value)}
                placeholder="Paste cookie here"
                className="w-full h-24 bg-black/60 border border-purple-900/50 rounded-xl p-4 text-sm text-gray-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all resize-none font-mono"
                disabled={!anyTypeEnabled}
                required
              />
            </div>
              <button
              type="submit"
                disabled={isLoading || !cookieInput.trim() || !anyTypeEnabled || !selectedTypeEnabled || taskStatus === "awaiting_confirm" || !hasEnoughCredits || stats.queue_active >= stats.queue_limit}
                className="w-full bg-gradient-to-r from-indigo-500 to-blue-600 hover:from-indigo-600 hover:to-blue-700 text-white font-bold py-3.5 px-4 rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading && taskStatus === "none" ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>{!hasEnoughCredits ? "Credit Not Enough" : stats.queue_active >= stats.queue_limit ? "Queue Full" : "Start Verification"}</>
              )}
            </button>
          </form>

          {taskStatus === "awaiting_confirm" && (
            <div className="mt-4 space-y-3 rounded-xl border border-yellow-500/30 bg-yellow-950/30 p-3">
              <p className="text-sm text-yellow-300 font-semibold">Profile fetched. Continue or cancel to proceed.</p>
              <p className="text-xs text-yellow-200/90">Cancel at this step will not charge any credits.</p>
              {activeProfile && (
                <div className="text-xs text-yellow-100/90 space-y-1">
                  <p>GitHub: {activeProfile.github_username || "-"}</p>
                  <p>Email: {activeProfile.email || "-"}</p>
                  <p>2FA: {activeProfile.has_2fa ? "Enabled" : "Disabled"}</p>
                  <p>Account Age: {activeProfile.age_days ?? 0} days</p>
                  <p>Criteria: {activeProfile.criteria_ok ? "PASS" : "FAIL"}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="rounded-lg border border-red-500/50 bg-red-900/40 px-3 py-2 text-sm font-semibold text-red-200 hover:bg-red-800/50"
                >
                  Cancel (No Charge)
                </button>
                <button
                  type="button"
                  onClick={handleContinue}
                  className="rounded-lg border border-green-500/50 bg-green-900/40 px-3 py-2 text-sm font-semibold text-green-200 hover:bg-green-800/50"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {taskStatus === "session_expired" && (
            <div className="mt-4 space-y-3 rounded-xl border border-amber-500/30 bg-amber-950/30 p-3">
              <p className="text-sm text-amber-300 font-semibold">GitHub session expired. Paste fresh cookies, then resume polling.</p>
              <div className="grid grid-cols-1 gap-2">
                <button
                  type="button"
                  onClick={handleResendCookies}
                  disabled={isLoading || !cookieInput.trim()}
                  className="rounded-lg border border-amber-400/60 bg-amber-800/40 px-3 py-2 text-sm font-semibold text-amber-100 hover:bg-amber-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? "Resuming..." : "Resend Cookies & Resume"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="bg-[#0b0310] p-4 rounded-2xl border border-purple-900/50 shadow-xl overflow-hidden">
          <div className="flex items-center gap-2 mb-3 border-b border-purple-900/50 pb-3">
            <Terminal className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-bold font-mono tracking-wider">
              PROCESS LOGS : {activeGithubName}
            </h2>
            {isLoading && <div className="ml-auto w-3 h-3 bg-green-500 rounded-full animate-pulse" />}
          </div>
          <p className="mb-2 text-[11px] text-purple-200/80">Indicator: {activeIndicator}</p>
          <p className="mb-1 text-[11px] text-purple-200/70">GitHub Username: <span className="text-white">{activeGithubRaw || activeGithubName}</span></p>
          <p className="mb-2 text-[11px] text-purple-200/70">GitHub Email: <span className="text-white">{activeGithubEmail}</span></p>
          <div className="h-48 overflow-y-auto font-mono text-xs text-green-400 space-y-1 pr-2 custom-scrollbar">
            {activeLogs.length === 0 && (
              <div>
                <span className="text-gray-500 mr-2">{'>'}</span>
                Waiting for verification logs...
              </div>
            )}
            {activeLogs.map((log, i) => (
              <div key={i}>
                <span className="text-gray-500 mr-2">{'>'}</span>
                {log.includes("ERROR") || log.includes("failed") || log.includes("rejected") || log.includes("gagal") || log.includes("ditolak")
                  ? <span className="text-red-400">{log}</span>
                  : log.includes("success") || log.includes("approved") || log.includes("valid") || log.includes("PASS") || log.includes("berhasil")
                  ? <span className="text-blue-400">{log}</span>
                  : log}
              </div>
            ))}
          </div>
        </div>

      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #111;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #4f46e5;
          border-radius: 4px;
        }
      `}} />
    </div>
  );
}
