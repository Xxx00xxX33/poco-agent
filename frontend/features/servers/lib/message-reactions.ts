import type {
  ServerConversationMessage,
  ServerConversationMessageReactionGroup,
} from "@/features/servers/model/types";

function toggleReactionGroups(
  groups: ServerConversationMessageReactionGroup[],
  emoji: string,
): ServerConversationMessageReactionGroup[] {
  const existing = groups.find((group) => group.emoji === emoji);
  if (!existing) {
    return [
      ...groups,
      {
        emoji,
        count: 1,
        reactedByCurrentUser: true,
        reactedByCurrentAgent: false,
        actors: [],
      },
    ];
  }
  if (existing.reactedByCurrentUser) {
    return groups
      .map((group) =>
        group.emoji === emoji
          ? {
              ...group,
              count: Math.max(0, group.count - 1),
              reactedByCurrentUser: false,
            }
          : group,
      )
      .filter((group) => group.count > 0);
  }
  return groups.map((group) =>
    group.emoji === emoji
      ? {
          ...group,
          count: group.count + 1,
          reactedByCurrentUser: true,
        }
      : group,
  );
}

export function toggleMessageReaction(
  message: ServerConversationMessage,
  emoji: string,
): ServerConversationMessage {
  return {
    ...message,
    reactions: toggleReactionGroups(message.reactions ?? [], emoji),
  };
}

export function updateMessageById(
  messages: ServerConversationMessage[],
  messageId: string,
  update: (message: ServerConversationMessage) => ServerConversationMessage,
): ServerConversationMessage[] {
  let changed = false;
  const next = messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    changed = true;
    return update(message);
  });
  return changed ? next : messages;
}
