import { ApiThread } from "@/types/dto";
import { Icons } from "./icons";
import { Text } from "./ui/Text";
import { cn } from "@/utils/cssUtils";

export function ThreadIcon() {
  return (
    <div className="w-8 bg-cyan-700 rounded-xl flex-shrink-0">
      <Icons.threadIcon className={cn(`text-brand-teal`)} />
    </div>
  );
}

interface ThreadItemProps {
  active: boolean;
  thread: ApiThread;
  onSwitchThread: () => void;
}

export function ThreadItem({
  thread,
  onSwitchThread,
  active,
}: ThreadItemProps) {
  const activeColor = "bg-tab-selected-onInset";

  return (
    <div
      className={cn(
        `cursor-pointer flex items-center justify-start py-3 pl-4 pr-8 rounded-lg h-16 gap-4 relative hover:bg-tab-selected-onInset`,
        active ? activeColor : ""
      )}
      onClick={onSwitchThread}
    >
      <div
        className={`w-12 h-12 ${activeColor} rounded-[12px] justify-center items-center gap-2 inline-flex flex-shrink-0`}
      >
        <ThreadIcon />
      </div>

      <div className="flex flex-col justify-center items-start gap-0.5 min-w-0">
        <div className="max-w-[230px] w-full min-w-0 inline-block">
          <Text kind="body2-bold" className="truncate">
            {thread.title}
          </Text>
        </div>
      </div>
    </div>
  );
}
