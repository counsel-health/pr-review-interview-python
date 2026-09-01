import { Button } from "./ui/Button";
import { Text } from "./ui/Text";
import { ApiThread, ApiUser } from "@/types/dto";
import { Input } from "./ui/Input";
import { ThreadItem } from "./ThreadItem";
import { useEffect, useState } from "react";
import { useDebouncedValue } from "@/utils/useDebouncedValue";

const MENU_WIDTH = 333;

interface LeftMenuProps {
  currentThreadId: string;
  setCurrentThreadId: (id: string) => void;
  threads: ApiThread[];
  onCreateThread: (title: string) => void;
  isPhysician: boolean;
  onToggleUser: () => void;
  physicians: ApiUser[];
  selectedPhysicianId: string | null;
  onSelectPhysician: (id: string) => void;
  onSearch: (query: string) => void;
}

export default function LeftMenu({
  currentThreadId,
  setCurrentThreadId,
  threads,
  onCreateThread,
  isPhysician,
  onToggleUser,
  physicians,
  selectedPhysicianId,
  onSelectPhysician,
  onSearch,
}: LeftMenuProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedQuery = useDebouncedValue(searchQuery, 250);

  useEffect(() => {
    onSearch(debouncedQuery);
  }, [debouncedQuery, onSearch]);

  return (
    <div
      style={{
        width: `${MENU_WIDTH}px`,
      }}
      className="inline-flex flex-col items-center transition-all h-[calc(100dvh)] whitespace-normal bg-background-inset"
    >
      <div className="flex space-between justify-start items-center w-full px-5 py-4 gap-3">
        <Text kind="h2-bold" className="text-nowrap">
          Counsel Health
        </Text>
        <div className="w-full"></div>
        <button
          onClick={onToggleUser}
          className="flex items-center gap-2 flex-shrink-0 cursor-pointer"
          title={isPhysician ? "Switch to Patient" : "Switch to Physician"}
        >
          <span className="text-xs text-neutral-500 text-nowrap">
            {isPhysician ? "MD" : "Pt"}
          </span>
          <div
            className={`relative w-8 h-[18px] rounded-full transition-colors ${
              isPhysician ? "bg-teal-500" : "bg-neutral-300"
            }`}
          >
            <div
              className={`absolute top-[2px] w-[14px] h-[14px] rounded-full bg-white shadow transition-transform ${
                isPhysician ? "translate-x-[15px]" : "translate-x-[2px]"
              }`}
            />
          </div>
        </button>
      </div>
      {isPhysician && physicians.length > 0 && (
        <div className="w-full px-4 pb-2">
          <select
            value={selectedPhysicianId ?? ""}
            onChange={(e) => onSelectPhysician(e.target.value)}
            className="w-full h-9 rounded-xs border border-input bg-white px-3 text-sm"
          >
            {physicians.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="w-full px-4 py-2 ">
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-white"
          placeholder="Search..."
        ></Input>
      </div>

      <div className="flex flex-col items-center w-full min-h-0">
        <div className="flex justify-between px-4 pb-4 w-full">
          <Button
            className="w-full p-3 h-12 rounded-lg justify-center items-center gap-2"
            onClick={() => {
              const title = window.prompt("Enter a title for the new thread:");
              if (title?.trim()) {
                onCreateThread(title.trim());
              }
            }}
          >
            <Text kind="body1">New Thread</Text>
          </Button>
        </div>
        <div className="flex flex-col gap-2 w-full overflow-scroll flex-grow border-t py-4 px-1">
          {threads.map((thread) => (
            <ThreadItem
              key={thread.id}
              thread={thread}
              onSwitchThread={() => setCurrentThreadId(thread.id)}
              active={thread.id === currentThreadId}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
