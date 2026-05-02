import Alert from '@mui/material/Alert'
import type { ReactNode } from 'react'
import { Component } from 'react'

type Props = {
  children: ReactNode
  fallback?: ReactNode
}

type State = {
  hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(): void {
    // Keep UI alive on render/runtime crashes inside heavy charts.
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback ?? <Alert severity="error">Component crashed. Please retry analysis.</Alert>
    }
    return this.props.children
  }
}
