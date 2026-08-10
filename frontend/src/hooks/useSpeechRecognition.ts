import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

interface SpeechAlternativeLike {
  transcript: string
}

interface SpeechResultLike {
  readonly length: number
  readonly isFinal: boolean
  [index: number]: SpeechAlternativeLike
}

interface SpeechResultListLike {
  readonly length: number
  [index: number]: SpeechResultLike
}

interface SpeechResultEventLike {
  readonly results: SpeechResultListLike
}

interface SpeechErrorEventLike {
  readonly error: string
}

interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onresult:
    | ((event: SpeechResultEventLike) => void)
    | null
  onerror:
    | ((event: SpeechErrorEventLike) => void)
    | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionLike
}

type SpeechWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor
  webkitSpeechRecognition?: SpeechRecognitionConstructor
}

interface UseSpeechRecognitionOptions {
  language?: string
  onTranscript: (transcript: string) => void
  onError: (message: string) => void
}

function getSpeechRecognitionConstructor():
  | SpeechRecognitionConstructor
  | null {
  if (typeof window === 'undefined') {
    return null
  }

  const speechWindow = window as SpeechWindow

  return (
    speechWindow.SpeechRecognition
    ?? speechWindow.webkitSpeechRecognition
    ?? null
  )
}

function getErrorMessage(error: string): string {
  switch (error) {
    case 'not-allowed':
    case 'service-not-allowed':
      return '未获得麦克风权限，请在浏览器中允许使用麦克风'

    case 'audio-capture':
      return '未检测到可用的麦克风'

    case 'no-speech':
      return '没有识别到语音，请重新尝试'

    case 'network':
      return '语音识别服务连接失败，请检查网络'

    default:
      return '语音识别失败，请重新尝试'
  }
}

export function useSpeechRecognition({
  language = 'zh-CN',
  onTranscript,
  onError,
}: UseSpeechRecognitionOptions) {
  const [listening, setListening] = useState(false)
  const recognitionRef =
    useRef<SpeechRecognitionLike | null>(null)
  const onTranscriptRef = useRef(onTranscript)
  const onErrorRef = useRef(onError)

  useEffect(() => {
    onTranscriptRef.current = onTranscript
    onErrorRef.current = onError
  }, [onTranscript, onError])

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort()
      recognitionRef.current = null
    }
  }, [])

  const supported =
    getSpeechRecognitionConstructor() !== null

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  const startListening = useCallback(() => {
    const Recognition =
      getSpeechRecognitionConstructor()

    if (!Recognition) {
      onErrorRef.current(
        '当前浏览器不支持语音输入，请使用 Chrome 或 Edge',
      )
      return
    }

    recognitionRef.current?.abort()

    const recognition = new Recognition()

    recognition.lang = language
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onresult = (event) => {
      let transcript = ''

      for (
        let index = 0;
        index < event.results.length;
        index += 1
      ) {
        transcript +=
          event.results[index][0]?.transcript ?? ''
      }

      onTranscriptRef.current(transcript.trim())
    }

    recognition.onerror = (event) => {
      if (event.error === 'aborted') {
        return
      }

      onErrorRef.current(
        getErrorMessage(event.error),
      )
      setListening(false)
    }

    recognition.onend = () => {
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null
      }

      setListening(false)
    }

    recognitionRef.current = recognition

    try {
      recognition.start()
      setListening(true)
    } catch {
      recognitionRef.current = null
      setListening(false)
      onErrorRef.current(
        '语音识别启动失败，请重新尝试',
      )
    }
  }, [language])

  return {
    supported,
    listening,
    startListening,
    stopListening,
  }
}