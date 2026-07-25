import { motion, AnimatePresence } from "motion/react";
import { 
  LayoutDashboard, 
  Upload, 
  Activity, 
  FileText, 
  History, 
  User, 
  LogOut,
  Menu,
  X
} from "lucide-react";
import { useState, useEffect } from "react";

export type PageType = "dashboard" | "upload" | "manual" | "reports" | "history" | "profile";

interface SidebarProps {
  currentPage: PageType;
  onPageChange: (page: PageType) => void;
  onLogout: () => void;
  userName: string;
  userPhoto: string;
}

export function Sidebar({ currentPage, onPageChange, onLogout, userName, userPhoto }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const checkDesktop = () => setIsDesktop(window.innerWidth >= 1024);
    checkDesktop();
    window.addEventListener("resize", checkDesktop);
    return () => window.removeEventListener("resize", checkDesktop);
  }, []);

  const menuItems = [
    { id: "dashboard" as PageType, label: "Dashboard", icon: LayoutDashboard },
    { id: "upload" as PageType, label: "Upload CSV", icon: Upload },
    { id: "manual" as PageType, label: "Manual Analysis", icon: Activity },
    { id: "reports" as PageType, label: "Reports", icon: FileText },
    { id: "history" as PageType, label: "History", icon: History },
    { id: "profile" as PageType, label: "Profile", icon: User },
  ];

  const handlePageChange = (page: PageType) => {
    onPageChange(page);
    setIsMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsMobileOpen(!isMobileOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-3 backdrop-blur-lg bg-white/70 border border-white/50 rounded-xl shadow-lg"
      >
        {isMobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Sidebar */}
      <AnimatePresence>
        {(isMobileOpen || isDesktop) && (
          <motion.div
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className={`fixed left-0 top-0 h-screen backdrop-blur-lg bg-white/70 border-r border-white/50 shadow-2xl z-40 ${
              isCollapsed ? "w-20" : "w-72"
            } transition-all duration-300`}
          >
            <div className="flex flex-col h-full p-4">
              {/* Logo & Toggle */}
              <div className="flex items-center justify-between mb-8 mt-2">
                {!isCollapsed && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-3"
                  >
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                      <Activity className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <div className="text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                        FPD
                      </div>
                      <div className="text-xs text-gray-600">Productivity</div>
                    </div>
                  </motion.div>
                )}
                <button
                  onClick={() => setIsCollapsed(!isCollapsed)}
                  className="hidden lg:block p-2 hover:bg-white/50 rounded-lg transition-colors"
                >
                  <Menu className="w-5 h-5" />
                </button>
              </div>

              {/* User Profile */}
              <motion.div
                className={`mb-6 p-4 bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl ${
                  isCollapsed ? "px-2" : ""
                }`}
              >
                <div className={`flex items-center gap-3 ${isCollapsed ? "justify-center" : ""}`}>
                  <img
                    src={userPhoto}
                    alt={userName}
                    className={`rounded-full border-2 border-white shadow-md ${
                      isCollapsed ? "w-10 h-10" : "w-12 h-12"
                    }`}
                  />
                  {!isCollapsed && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="overflow-hidden"
                    >
                      <div className="text-sm font-semibold truncate">{userName}</div>
                      <div className="text-xs text-gray-600">Active User</div>
                    </motion.div>
                  )}
                </div>
              </motion.div>

              {/* Menu Items */}
              <nav className="flex-1 space-y-2">
                {menuItems.map((item, index) => {
                  const Icon = item.icon;
                  const isActive = currentPage === item.id;

                  return (
                    <motion.button
                      key={item.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => handlePageChange(item.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ${
                        isActive
                          ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg"
                          : "hover:bg-white/50 text-gray-700"
                      } ${isCollapsed ? "justify-center px-2" : ""}`}
                    >
                      <Icon className={`${isCollapsed ? "w-6 h-6" : "w-5 h-5"} ${isActive ? "animate-pulse" : ""}`} />
                      {!isCollapsed && (
                        <span className="text-sm font-medium">{item.label}</span>
                      )}
                      {isActive && !isCollapsed && (
                        <motion.div
                          layoutId="activeIndicator"
                          className="ml-auto w-2 h-2 bg-white rounded-full"
                        />
                      )}
                    </motion.button>
                  );
                })}
              </nav>

              {/* Logout Button */}
              <motion.button
                onClick={onLogout}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-all duration-300 shadow-md hover:shadow-lg ${
                  isCollapsed ? "justify-center px-2" : ""
                }`}
              >
                <LogOut className={`${isCollapsed ? "w-6 h-6" : "w-5 h-5"}`} />
                {!isCollapsed && <span className="text-sm font-medium">Logout</span>}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setIsMobileOpen(false)}
          className="lg:hidden fixed inset-0 bg-black/20 backdrop-blur-sm z-30"
        />
      )}
    </>
  );
}
