/* Specify "use client" for Client-side rendered components. Any components that use
   React hooks or browser-specific APIs should be marked as "use client". All children
   of a "use client" component will also be treated as "use client".
   More details: https://nextjs.org/docs/app/building-your-application/rendering/client-components
*/
"use client";

import { Chat } from "@/components/Chat";
import LeftMenu from "@/components/LeftMenu";
import * as api from "@/utils/api";
import { ApiThread, ApiUser } from "@/types/dto";
import { handlePromiseRejection } from "@/utils/miscUtils";
import { useCallback, useEffect, useState } from "react";

const PATIENT_USER_ID = "user1";

export default function ChatApp() {
  const [currentThreadId, setCurrentThreadId] = useState("");
  const [currentUserId, setCurrentUserId] = useState(PATIENT_USER_ID);
  const [selectedPhysicianId, setSelectedPhysicianId] = useState<string | null>(null);
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [threads, setThreads] = useState<ApiThread[]>([]);

  const physicians = users.filter((u) => u.is_physician);
  const isPhysician = currentUserId !== PATIENT_USER_ID;

  const handleCreateThread = async (title: string) => {
    const physicianId = selectedPhysicianId ?? physicians[0]?.id;
    if (!physicianId) return;
    const newThread = await api.createThread(title, [physicianId, PATIENT_USER_ID]);
    setThreads((prev) => [newThread, ...prev]);
    setCurrentThreadId(newThread.id);
  };

  const handleToggleUser = () => {
    if (isPhysician) {
      setCurrentUserId(PATIENT_USER_ID);
    } else {
      const nextPhysicianId = selectedPhysicianId ?? physicians[0]?.id;
      if (nextPhysicianId) {
        setSelectedPhysicianId(nextPhysicianId);
        setCurrentUserId(nextPhysicianId);
      }
    }
  };

  const handleSelectPhysician = (id: string) => {
    setSelectedPhysicianId(id);
    setCurrentUserId(id);
  };

  const handleSearch = useCallback((query: string) => {
    handlePromiseRejection(async () => {
      const results = await api.getThreads(query);
      setThreads(results);
    }, "Failed to search threads");
  }, []);

  const handleMessageSent = (threadId: string) => {
    setThreads((prev) => {
      const idx = prev.findIndex((t) => t.id === threadId);
      if (idx <= 0) return prev;
      const next = [...prev];
      const [moved] = next.splice(idx, 1);
      next.unshift(moved);
      return next;
    });
  };

  const currentThread =
    threads.find((thread) => thread.id === currentThreadId) ?? null;

  useEffect(() => {
    handlePromiseRejection(async () => {
      const users = await api.getUsers();
      setUsers(users);

      const threads = await api.getThreads();
      setThreads(threads);
    }, "Failed to fetch data");
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-between">
      <div
        className={`overflow-x-hidden whitespace-nowrap bg-background-inset relative flex w-full`}
      >
        <LeftMenu
          currentThreadId={currentThreadId}
          setCurrentThreadId={setCurrentThreadId}
          threads={threads}
          onCreateThread={handleCreateThread}
          isPhysician={isPhysician}
          onToggleUser={handleToggleUser}
          physicians={physicians}
          selectedPhysicianId={selectedPhysicianId}
          onSelectPhysician={handleSelectPhysician}
          onSearch={handleSearch}
        />
        <div className="items-center whitespace-normal w-full inline-flex flex-shrink-1 flex-col h-[calc(100dvh)] bg-background-surface align-top transition-opacity relative min-w-0">
          <Chat
            users={users}
            thread={currentThread}
            currentUserId={currentUserId}
            onMessageSent={handleMessageSent}
          />
        </div>
      </div>
    </main>
  );
}
