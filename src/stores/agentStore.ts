import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { OrchestratorAgent } from '@/agents/specialized/OrchestratorAgent';
import type { AgentMessage, AgentState, AgentResponse } from '@/agents/types';
import type { LLMConfig } from '@/agents/llm/LLMProvider';

/** Data extracted from Form 16 OCR and stored for cross-page prefill. */
export interface Form16Data {
  gross_salary?: number
  employer_name?: string
  tds_paid?: number
  pan?: string
  fy?: string
}

/** A single RAG source returned by the backend alongside a chat reply. */
export interface RagSource {
  id?: string | number
  url?: string
  title?: string
  section?: string
  source?: string
  score?: number
  description?: string
}

export const useAgentStore = defineStore('agent', () => {
  // State
  const orchestrator = ref<OrchestratorAgent | null>(null);
  const isInitialized = ref(false);
  const isProcessing = ref(false);
  const currentAgentStatuses = ref<Record<string, AgentState>>({});
  const messageHistory = ref<AgentMessage[]>([]);
  const lastResponse = ref<AgentResponse | null>(null);

  /** Form 16 OCR data stored after a successful upload in Documents.vue.
   *  NewFiling.vue reads this on mount to prefill salary/TDS fields. */
  const form16Data = ref<Form16Data | null>(null);

  /** Latest RAG sources returned by the backend alongside a chat reply.
   *  Chat.vue reads this to populate the sources sidebar. */
  const ragSources = ref<RagSource[]>([]);

  const currentProvider = ref<LLMConfig>({
    provider: 'qwen',
    model: 'qwen/qwen-2.5-72b-instruct:free',
    temperature: 0.7,
    maxTokens: 2000
  });

  // Computed
  const allAgentsIdle = computed(() => {
    return Object.values(currentAgentStatuses.value).every(
      status => status.status === 'idle' || status.status === 'completed'
    );
  });

  const activeAgents = computed(() => {
    return Object.entries(currentAgentStatuses.value)
      .filter(([_, status]) => status.status !== 'idle')
      .map(([role, _]) => role);
  });

  // Actions
  function initialize() {
    if (!isInitialized.value) {
      orchestrator.value = new OrchestratorAgent(currentProvider.value);
      isInitialized.value = true;
      console.log('AI Agent System initialized with provider:', currentProvider.value.provider);
    }
  }

  function setProvider(providerConfig: LLMConfig) {
    currentProvider.value = providerConfig;
    // Reinitialize with new provider
    if (orchestrator.value) {
      orchestrator.value = new OrchestratorAgent(currentProvider.value);
      console.log('AI Agent System reinitialized with provider:', currentProvider.value.provider);
    }
  }

  async function sendMessage(messageContent: string): Promise<AgentResponse> {
    if (!orchestrator.value) {
      initialize();
    }

    isProcessing.value = true;

    try {
      const message: AgentMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: messageContent,
        timestamp: new Date()
      };

      // Add to history
      messageHistory.value.push(message);

      // Get response from orchestrator
      const response = await orchestrator.value!.generateResponse(message);

      // Add AI response to history
      const aiMessage: AgentMessage = {
        id: `msg-${Date.now()}-ai`,
        role: 'agent',
        content: response.message,
        agentRole: 'orchestrator',
        timestamp: new Date(),
        reasoning: response.reasoning
      };

      messageHistory.value.push(aiMessage);
      lastResponse.value = response;

      // Update agent statuses
      updateAgentStatuses();

      return response;
    } catch (error) {
      console.error('Error processing message:', error);
      
      // Try to provide a helpful error message
      let errorMessage = 'An error occurred while processing your message.';
      if (error instanceof Error) {
        if (error.message.includes('API key')) {
          errorMessage = `API Configuration Error: ${error.message}. Please check your API keys in the .env file or switch to a different provider.`;
        } else if (error.message.includes('API error')) {
          errorMessage = `Provider Error: ${error.message}. The AI provider may be experiencing issues. Try switching to a different provider (GLM, Gemini, or Llama).`;
        } else {
          errorMessage = `Error: ${error.message}`;
        }
      }
      
      // Create error response
      const errorResponse: AgentResponse = {
        agentRole: 'orchestrator',
        message: errorMessage,
        confidence: 0,
        success: false,
        reasoning: ['Error occurred during processing'],
        data: { error: error instanceof Error ? error.message : String(error) }
      };
      
      lastResponse.value = errorResponse;
      throw error;
    } finally {
      isProcessing.value = false;
    }
  }

  async function processTask(taskType: string, taskInput: any): Promise<AgentResponse> {
    if (!orchestrator.value) {
      initialize();
    }

    isProcessing.value = true;

    try {
      const task = {
        id: `task-${Date.now()}`,
        agentRole: 'orchestrator' as const,
        type: taskType,
        priority: 'medium' as const,
        status: 'pending' as const,
        input: taskInput,
        createdAt: new Date()
      };

      const response = await orchestrator.value!.processTask(task);
      lastResponse.value = response;

      updateAgentStatuses();

      return response;
    } catch (error) {
      console.error('Error processing task:', error);
      throw error;
    } finally {
      isProcessing.value = false;
    }
  }

  function updateAgentStatuses() {
    if (orchestrator.value) {
      currentAgentStatuses.value = orchestrator.value.getAllAgentStatuses();
    }
  }

  function clearHistory() {
    messageHistory.value = [];
    lastResponse.value = null;
  }

  function getAgentState(agentRole: string): AgentState | null {
    return currentAgentStatuses.value[agentRole] || null;
  }

  // Tax-specific helper functions
  async function calculateTax(taxData: {
    taxableIncome: number;
    filingStatus: string;
  }): Promise<AgentResponse> {
    return await processTask('calculate_tax', taxData);
  }

  async function calculateCredits(creditData: {
    dependents: number;
    agi: number;
    filingStatus: string;
    earnedIncome?: number;
  }): Promise<AgentResponse> {
    return await processTask('calculate_credits', creditData);
  }

  async function analyzeScenarios(scenarios: any[]): Promise<AgentResponse> {
    return await processTask('scenario_analysis', { scenarios });
  }

  async function processDocument(documentData: any): Promise<AgentResponse> {
    return await processTask('process_document', documentData);
  }

  async function getAdvisory(context: any): Promise<AgentResponse> {
    return await processTask('provide_advice', context);
  }

  return {
    // State
    isInitialized,
    isProcessing,
    currentAgentStatuses,
    messageHistory,
    lastResponse,
    currentProvider,
    form16Data,
    ragSources,

    // Computed
    allAgentsIdle,
    activeAgents,

    // Actions
    initialize,
    sendMessage,
    processTask,
    updateAgentStatuses,
    clearHistory,
    getAgentState,
    setProvider,

    // Tax-specific helpers
    calculateTax,
    calculateCredits,
    analyzeScenarios,
    processDocument,
    getAdvisory
  };
});
