import { ApiMessage, ApiUser } from "@/types/dto";
import { PhysicianProfileCircle } from "./PhysicianProfileCircle";

interface TextChatMessageProps {
  message: ApiMessage;
  user: ApiUser;
}

const PHYSICIAN_COLORS = ["text-brand-teal", "text-brand-purple", "text-brand-orange"];

const physicianColorClass = (userId: string) => {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = (hash * 31 + userId.charCodeAt(i)) | 0;
  }
  return PHYSICIAN_COLORS[Math.abs(hash) % PHYSICIAN_COLORS.length];
};

export const TextChatMessage: React.FC<TextChatMessageProps> = ({
  message,
  user,
}) => {
  const physicianColor = physicianColorClass(user.id);
  return (
    <div
      className={`flex flex-col w-full min-w-0 ${
        !user.is_physician ? "items-end" : "items-start"
      }`}
    >
      {user.is_physician && (
        <div className="flex items-center">
          <div className="flex items-center gap-2 mb-3 cursor-pointer">
            <PhysicianProfileCircle className="w-6 h-6" colorClassName={physicianColor} />
            <div className={`text-sm ${physicianColor}`}>
              {user.name}
            </div>
          </div>
        </div>
      )}
      {user.is_physician ? (
        <div style={{ overflowWrap: "anywhere" }}>{message.message}</div>
      ) : (
        <>
          <div
            className={`chatMarkdown flex flex-col items-center bg-bubble-patient-background text-button-secondary-content rounded-md px-4 py-3 max-w-[73%] whitespace-pre-wrap`}
            style={{ overflowWrap: "anywhere" }}
          >
            {message.message}
          </div>
        </>
      )}
    </div>
  );
};
