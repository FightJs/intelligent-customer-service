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
      return '浏览器语音服务仍无法连接，请检查网络或代理，也可以继续键盘输入'

    default:
      return '语音识别失败，请重新尝试'
  }
}

function getPermissionErrorMessage(error: unknown): string {
  const errorName = (
    typeof error === 'object'
    && error !== null
    && 'name' in error
    && typeof error.name === 'string'
  )
    ? error.name
    : ''

  if (
    errorName === 'NotAllowedError'
    || errorName === 'SecurityError'
  ) {
    return '未获得麦克风权限，请在浏览器地址栏中允许使用麦克风'
  }

  if (
    errorName === 'NotFoundError'
    || errorName === 'DevicesNotFoundError'
  ) {
    return '未检测到可用的麦克风'
  }

  return '无法访问麦克风，请检查系统和浏览器的麦克风设置'
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
  const shouldListenRef = useRef(false)
  const restartTimerRef = useRef<number | null>(null)
  const retryCountRef = useRef(0)
  const unexpectedEndCountRef = useRef(0)

  useEffect(() => {
    onTranscriptRef.current = onTranscript
    onErrorRef.current = onError
  }, [onTranscript, onError])

  useEffect(() => {
    return () => {
      shouldListenRef.current = false

      if (restartTimerRef.current !== null) {
        window.clearTimeout(restartTimerRef.current)
        restartTimerRef.current = null
      }

      recognitionRef.current?.abort()
      recognitionRef.current = null
    }
  }, [])

  const supported =
    getSpeechRecognitionConstructor() !== null

  const stopListening = useCallback(() => {
    shouldListenRef.current = false
    retryCountRef.current = 0
    unexpectedEndCountRef.current = 0

    if (restartTimerRef.current !== null) {
      window.clearTimeout(restartTimerRef.current)
      restartTimerRef.current = null
    }

    const recognition = recognitionRef.current
    recognitionRef.current = null

    try {
      recognition?.stop()
    } catch {
      recognition?.abort()
    }

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

    if (shouldListenRef.current) {
      return
    }

    shouldListenRef.current = true
    retryCountRef.current = 0
    unexpectedEndCountRef.current = 0
    setListening(true)

    const scheduleRestart = (
      startRecognition: () => void,
      delay: number,
    ) => {
      if (restartTimerRef.current !== null) {
        window.clearTimeout(restartTimerRef.current)
      }

      restartTimerRef.current = window.setTimeout(() => {
        restartTimerRef.current = null

        if (shouldListenRef.current) {
          startRecognition()
        }
      }, delay)
    }

    const startRecognition = () => {
      if (!shouldListenRef.current) {
        return
      }

      const recognition = new Recognition()

      recognition.lang = language
      recognition.continuous = true
      recognition.interimResults = true
      recognition.maxAlternatives = 1

      recognition.onresult = (event) => {
        if (recognitionRef.current !== recognition) {
          return
        }

        retryCountRef.current = 0
        unexpectedEndCountRef.current = 0

        let transcript = ''

        for (
          let index = 0;
          index < event.results.length;
          index += 1
        ) {
          transcript += (
            event.results[index][0]?.transcript
            ?? ''
          )
        }

        onTranscriptRef.current(
          transcript.trim(),
        )
      }

      recognition.onerror = (event) => {
        if (
          recognitionRef.current
          !== recognition
        ) {
          return
        }

        if (event.error === 'aborted') {
          return
        }

        recognitionRef.current = null

        const retryable = (
          event.error === 'network'
          || event.error === 'no-speech'
        )

        if (
          retryable
          && shouldListenRef.current
          && retryCountRef.current < 1
        ) {
          retryCountRef.current += 1
          scheduleRestart(
            startRecognition,
            600,
          )
          return
        }

        shouldListenRef.current = false
        setListening(false)
        onErrorRef.current(
          getErrorMessage(event.error),
        )
      }

      recognition.onend = () => {
        if (
          recognitionRef.current
          !== recognition
        ) {
          return
        }

        recognitionRef.current = null

        if (!shouldListenRef.current) {
          setListening(false)
          return
        }

        unexpectedEndCountRef.current += 1

        if (
          unexpectedEndCountRef.current
          <= 2
        ) {
          scheduleRestart(
            startRecognition,
            300,
          )
          return
        }

        shouldListenRef.current = false
        setListening(false)
        onErrorRef.current(
          '语音识别多次中断，请点击麦克风重试或继续键盘输入',
        )
      }

      recognitionRef.current = recognition

      try {
        recognition.start()
      } catch {
        recognitionRef.current = null
        shouldListenRef.current = false
        setListening(false)
        onErrorRef.current(
          '语音识别启动失败，请稍后重试或继续键盘输入',
        )
      }
    }

    const mediaDevices = (
      navigator.mediaDevices
    )

    if (!mediaDevices?.getUserMedia) {
      startRecognition()
      return
    }

    void mediaDevices.getUserMedia({
      audio: true,
    }).then((stream) => {
      for (const track of stream.getTracks()) {
        track.stop()
      }

      if (shouldListenRef.current) {
        startRecognition()
      }
    }).catch((error: unknown) => {
      shouldListenRef.current = false
      setListening(false)
      onErrorRef.current(
        getPermissionErrorMessage(error),
      )
    })
  }, [language])

  return {
    supported,
    listening,
    startListening,
    stopListening,
  }
}
