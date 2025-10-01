<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';

  let inputText: string = $state('');
  let isLoading: boolean = $state(false);
  let summaryText: string = $state('');
  let toastMessage: string | null = $state(null);

  interface HealthcheckResponse {
    status: string;
    timestamp: string;
    uptime: number;
    app_ver: string;
    app_env: string;
    apikey_set: boolean;
    disk_free_bytes: number;
    message: string | null;
  }

  async function healthcheck() {
    const healthcheckURL = 'http://127.0.0.1:8000/healthcheck';
    console.log('Pinging healthcheck endpoint: ${healthcheckURL}');

    try {
      const response = await fetch(healthcheckURL);

      if (response.ok) {
        const data: HealthcheckResponse = await response.json();
        console.log(data.status);
      } else {
        console.error(response.status);
      }
    } catch (error) {
      console.error('Backend unreachable. Check if server is running.', error);
    }
  }

  async function handleSummarize() {
    summaryText = '';
    isLoading = true;

    const apiUrl = 'http://127.0.0.1:8000/summarize';

    // !TODO Improve this to be more efficient
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          inputText: inputText,
        }),
      });
      const data = await response.json();

      if (response.ok) {
        summaryText = data.summary;
      } else {
        console.error(
          'Failed to generate summary:',
          data.summary || 'Unknown error',
        );
        summaryText = data.summary || 'Error: Failed to process summary.';
      }
    } catch (error) {
      console.error('Network error:', error);
      summaryText = 'Error: Failed to reach the summary backend.';
    } finally {
      isLoading = false;
    }
  }

  function handleFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const fileList = target.files;

    if (!fileList || fileList.length === 0) {
      console.log('File selection aborted.');
      inputText = '';
      return;
    }

    const file = fileList[0];

    // !TODO validate file is of correct type

    const reader = new FileReader();
    reader.onload = (e) => {
      inputText = e?.target?.result?.toString() ?? '';
    };

    reader.onerror = (e) => {
      console.error('Error reading file:', e);
      toastMessage = 'Could not read file. Check console.';
      setTimeout(() => {
        toastMessage = null;
      }, 3000);
      inputText = '';
    };

    reader.readAsText(file);
  }

  function handleCopy() {
    navigator.clipboard
      .writeText(summaryText)
      .then(() => {
        toastMessage = 'Copied to clipboard';
        setTimeout(() => {
          toastMessage = null;
        }, 3000);
      })
      .catch((err) => {
        console.error('Could not copy text: ', err);
        toastMessage = 'Could not copy to clipboard';
        setTimeout(() => {
          toastMessage = null;
        }, 3000);
      });
  }

  function handleDownload() {
    const blob = new Blob([summaryText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');

    a.href = url;
    a.download = 'summary.txt';

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  onMount(() => {
    healthcheck();
  });
</script>

<div class="min-h-screen flex flex-col items-center justify-center">
  <div
    class="flex flex-col w-full max-w-2xl min-w-1/2 gap-4 mb-5 p-5 text-blue-950 bg-blue-300 border border-blue-400 rounded-lg shadow-sm"
  >
    <h2 class="text-xl font-semibold text-blue-950">Enter your Notes Here:</h2>
    <textarea
      bind:value={inputText}
      placeholder="Enter text here..."
      rows={summaryText ? 3 : 10}
      class="w-full p-3 bg-blue-200 border border-blue-400 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 font-sans"
    ></textarea>
    <input
      type="file"
      accept=".txt,.md"
      onchange={handleFileUpload}
      class="text-sm text-blue-950 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-300 file:text-blue-950 hover:file:bg-blue-200"
    />
    <button
      onclick={handleSummarize}
      disabled={!inputText.trim() || isLoading}
      class="py-2 px-4 rounded-lg font-bold bg-blue-600 text-blue-950 transition duration-200 hover:bg-blue-700 disabled:bg-gray-600 disabled:text-gray-900 disabled:cursor-not-allowed"
      >Summarize</button
    >

    {#if summaryText}
      <div
        class="mt-5 p-4 bg-blue-200 text-blue-950 border border-blue-600 border-l-8 rounded-md"
      >
        <h3 class="text-lg font-semibold mb-2 text-blue-800">Summary:</h3>
        <p class="whitespace-pre-wrap">{summaryText}</p>
      </div>
      <div class="flex gap-3 mt-4">
        <button
          onclick={handleCopy}
          class="py-2 px-4 rounded-lg bg-blue-500 text-blue-950 font-medium hover:bg-blue-700 transition duration-150"
          >Copy to Clipboard</button
        >
        <button
          onclick={handleDownload}
          class="py-2 px-4 rounded-lg bg-blue-500 text-blue-950 font-medium hover:bg-blue-700 transition duration-150"
          >Download Summary</button
        >
      </div>
    {/if}
  </div>

  {#if isLoading}
    <div
      class="fixed bottom-1/2 left-1/2 transform -translate-x-1/2 p-4 rounded-lg shadow-xl flex items-center gap-4 mt-5 bg-yellow-100 border border-yellow-400 text-yellow-800 z-50 transition-opacity duration-300"
    >
      <p>Processing request... Please wait.</p>
      <div
        class="animate-spin border-4 border-t-4 border-gray-300 border-t-blue-600 rounded-full w-5 h-5"
      ></div>
    </div>
  {/if}

  {#if toastMessage}
    <div
      class="fixed bottom-1/2 left-1/2 transform -translate-x-1/2 p-4 rounded-lg shadow-xl bg-gray-800 text-white text-sm z-50 transition-opacity duration-300"
    >
      <p>{toastMessage}</p>
    </div>
  {/if}
</div>
