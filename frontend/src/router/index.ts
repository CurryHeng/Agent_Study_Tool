import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated } from '../api/client'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import QuestionBankView from '../views/QuestionBankView.vue'
import AddQuestionView from '../views/AddQuestionView.vue'
import RegisterView from '../views/RegisterView.vue'
import ReviewView from '../views/ReviewView.vue'
import WrongBookView from '../views/WrongBookView.vue'
import MindMapView from '../views/MindMapView.vue'
import SettingsView from '../views/SettingsView.vue'
import StatsView from '../views/StatsView.vue'
import HistoryView from '../views/HistoryView.vue'
import LibraryView from '../views/LibraryView.vue'
import KnowledgeGraphView from '../views/KnowledgeGraphView.vue'
import VisualizationView from '../views/VisualizationView.vue'
import AgentChatView from '../views/AgentChatView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/register', component: RegisterView },
    { path: '/', component: DashboardView },
    { path: '/questions', component: QuestionBankView },
    { path: '/questions/add', component: AddQuestionView },
    { path: '/review', component: ReviewView },
    { path: '/wrong', component: WrongBookView },
    { path: '/mindmap', redirect: '/visualization?tab=mindmap' },
    { path: '/knowledge-graph', redirect: '/visualization?tab=graph' },
    { path: '/visualization', component: VisualizationView },
    { path: '/stats', component: StatsView },
    { path: '/history', component: HistoryView },
    { path: '/library', component: LibraryView },
    { path: '/knowledge-graph', component: KnowledgeGraphView },
    { path: '/assistant', component: AgentChatView },
    { path: '/settings', component: SettingsView },
  ],
})

router.beforeEach((to) => {
  if (!isAuthenticated() && to.path !== '/login' && to.path !== '/register') {
    return '/login'
  }
  return true
})

export default router
