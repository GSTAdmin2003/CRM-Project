<script>
  import ConversationList from './ConversationList.svelte';
  import ChatPane from './ChatPane.svelte';

  export let apiUrls = {};

  let selectedConversation = null;
</script>

<div class="flex h-[calc(100vh-4rem)] bg-white">
  <!-- Left pane: conversation list (fixed width) -->
  <div class="w-72 flex-shrink-0 flex flex-col overflow-hidden">
    <ConversationList
      {apiUrls}
      selectedId={selectedConversation?.id ?? null}
      onSelect={(conv) => (selectedConversation = conv)}
    />
  </div>

  <!-- Right pane: chat -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <ChatPane conversation={selectedConversation} {apiUrls} />
  </div>
</div>
