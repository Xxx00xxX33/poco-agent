import type {
  ServerChannelMemberItem,
  ServerConversationMessage,
} from "@/features/servers/model/types";

export interface MentionCandidate {
  id: string;
  label: string;
  handle: string;
  kind: "agent" | "human";
  description?: string | null;
}

function getMessageTimestamp(message: ServerConversationMessage): number {
  const timestamp = Date.parse(message.createdAt);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

export function sortMessagesChronologically(
  messages: ServerConversationMessage[],
): ServerConversationMessage[] {
  return [...messages].sort((left, right) => {
    const timestampDiff = getMessageTimestamp(left) - getMessageTimestamp(right);
    if (timestampDiff !== 0) {
      return timestampDiff;
    }
    return left.id.localeCompare(right.id);
  });
}

export function buildHumanMentionCandidates(
  members: ServerChannelMemberItem[],
  currentUserId?: string | null,
): MentionCandidate[] {
  const excludedUserId = currentUserId?.trim();
  return members
    .filter((member) => !excludedUserId || member.userId !== excludedUserId)
    .map((member) => ({
      id: member.userId,
      label: member.userId,
      handle: member.userId,
      kind: "human",
    }));
}
