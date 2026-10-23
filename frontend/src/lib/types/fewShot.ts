export interface FewShotExample {
    input?: string
    output?: string
}

export interface ExampleEditorProps {
    nodeID: string
    exampleIndex: number
    example: FewShotExample
    onSave: () => void
    onDiscard: () => void
    onContentChange: (content: string, tab: 'input' | 'output') => void
}

export interface FewShotExamplesProps {
    nodeID: string
    examples: FewShotExample[]
    onChange: (examples: FewShotExample[]) => void
}

export interface FewShotExamplesEditorProps extends FewShotExamplesProps {
    readOnly?: boolean
}
