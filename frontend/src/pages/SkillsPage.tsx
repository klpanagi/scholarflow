import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import {
  Puzzle,
  Plus,
  Save,
  Trash2,
  Wrench,
  Globe,
  Lock,
} from "lucide-react"

interface BuiltinTool {
  name: string
  description: string
}

interface Skill {
  id: string
  name: string
  description: string
  prompt_template: string
  builtin_tools: string[]
  custom_tools: any[]
  input_schema: Record<string, any> | null
  output_schema: Record<string, any> | null
  tags: string[]
  is_public: boolean
  created_at: string
  updated_at: string
}

export default function SkillsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [tagInput, setTagInput] = useState("")

  const [form, setForm] = useState({
    name: "",
    description: "",
    prompt_template: "",
    builtin_tools: [] as string[],
    custom_tools: [] as any[],
    input_schema: "",
    output_schema: "",
    tags: [] as string[],
    is_public: false,
  })

  const { data: skills = [] } = useQuery<Skill[]>({
    queryKey: ["skills"],
    queryFn: async () => {
      const { data } = await api.get("/skills/")
      return data || []
    },
  })

  const { data: builtinTools = [] } = useQuery<BuiltinTool[]>({
    queryKey: ["builtin-tools"],
    queryFn: async () => {
      const { data } = await api.get("/skills/builtin-tools")
      return data || []
    },
  })

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post("/skills/", payload)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      setSelectedSkill(data)
      setIsCreating(false)
      toast({ title: "Skill created" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to create skill",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: any }) => {
      const { data } = await api.patch(`/skills/${id}`, payload)
      return data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      setSelectedSkill(data)
      toast({ title: "Skill updated" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update skill",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/skills/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] })
      setSelectedSkill(null)
      toast({ title: "Skill deleted" })
    },
    onError: (error: any) => {
      toast({
        title: "Failed to delete skill",
        description: error.response?.data?.detail || "Unknown error",
        variant: "destructive",
      })
    },
  })

  useEffect(() => {
    if (selectedSkill && !isCreating) {
      setForm({
        name: selectedSkill.name,
        description: selectedSkill.description,
        prompt_template: selectedSkill.prompt_template,
        builtin_tools: selectedSkill.builtin_tools || [],
        custom_tools: selectedSkill.custom_tools || [],
        input_schema: selectedSkill.input_schema
          ? JSON.stringify(selectedSkill.input_schema, null, 2)
          : "",
        output_schema: selectedSkill.output_schema
          ? JSON.stringify(selectedSkill.output_schema, null, 2)
          : "",
        tags: selectedSkill.tags || [],
        is_public: selectedSkill.is_public,
      })
      setTagInput((selectedSkill.tags || []).join(", "))
    }
  }, [selectedSkill, isCreating])

  const handleNew = () => {
    setIsCreating(true)
    setSelectedSkill(null)
    setForm({
      name: "",
      description: "",
      prompt_template: "",
      builtin_tools: [],
      custom_tools: [],
      input_schema: "",
      output_schema: "",
      tags: [],
      is_public: false,
    })
    setTagInput("")
  }

  const buildPayload = () => {
    let input_schema = null
    let output_schema = null
    try {
      if (form.input_schema.trim()) input_schema = JSON.parse(form.input_schema)
    } catch {
      toast({ title: "Invalid input schema JSON", variant: "destructive" })
      return null
    }
    try {
      if (form.output_schema.trim()) output_schema = JSON.parse(form.output_schema)
    } catch {
      toast({ title: "Invalid output schema JSON", variant: "destructive" })
      return null
    }
    return {
      name: form.name,
      description: form.description,
      prompt_template: form.prompt_template,
      builtin_tools: form.builtin_tools,
      custom_tools: form.custom_tools,
      input_schema,
      output_schema,
      tags: tagInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      is_public: form.is_public,
    }
  }

  const handleSave = () => {
    if (!form.name.trim()) {
      toast({ title: "Name is required", variant: "destructive" })
      return
    }
    if (!form.prompt_template.trim()) {
      toast({ title: "Prompt template is required", variant: "destructive" })
      return
    }
    const payload = buildPayload()
    if (!payload) return

    if (isCreating) {
      createMutation.mutate(payload)
    } else if (selectedSkill) {
      updateMutation.mutate({ id: selectedSkill.id, payload })
    }
  }

  const handleDelete = () => {
    if (selectedSkill) {
      deleteMutation.mutate(selectedSkill.id)
    }
  }

  const toggleBuiltinTool = (toolName: string) => {
    setForm((prev) => ({
      ...prev,
      builtin_tools: prev.builtin_tools.includes(toolName)
        ? prev.builtin_tools.filter((t) => t !== toolName)
        : [...prev.builtin_tools, toolName],
    }))
  }

  const updateForm = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="flex gap-6 h-full">
      {/* Left Panel - Skill List */}
      <div className="w-80 shrink-0 space-y-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Skills</h2>
          <Button size="sm" onClick={handleNew}>
            <Plus className="h-4 w-4 mr-1" /> New
          </Button>
        </div>

        {skills.map((skill) => (
          <Card
            key={skill.id}
            className={`cursor-pointer transition-colors ${
              selectedSkill?.id === skill.id ? "border-primary" : ""
            }`}
            onClick={() => {
              setSelectedSkill(skill)
              setIsCreating(false)
            }}
          >
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Puzzle className="h-4 w-4 text-primary" />
                  <span className="font-medium text-sm">{skill.name}</span>
                </div>
                {skill.is_public ? (
                  <Globe className="h-3 w-3 text-muted-foreground" />
                ) : (
                  <Lock className="h-3 w-3 text-muted-foreground" />
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {skill.description || "No description"}
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {skill.builtin_tools.slice(0, 3).map((t) => (
                  <Badge key={t} variant="secondary" className="text-xs">
                    {t}
                  </Badge>
                ))}
                {skill.builtin_tools.length > 3 && (
                  <Badge variant="secondary" className="text-xs">
                    +{skill.builtin_tools.length - 3}
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}

        {skills.length === 0 && (
          <Card>
            <CardContent className="py-6 text-center text-sm text-muted-foreground">
              No skills yet. Create one to get started.
            </CardContent>
          </Card>
        )}
      </div>

      {/* Right Panel - Skill Editor */}
      <div className="flex-1 space-y-6 overflow-y-auto">
        {selectedSkill || isCreating ? (
          <>
            {/* Basic Info */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Puzzle className="h-5 w-5" />
                      {isCreating ? "New Skill" : `Edit: ${selectedSkill?.name}`}
                    </CardTitle>
                    <CardDescription>
                      Define what this skill does and how agents should use it
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {!isCreating && (
                      <Button variant="destructive" size="sm" onClick={handleDelete}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                    <Button size="sm" onClick={handleSave}>
                      <Save className="h-4 w-4 mr-1" /> Save
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium">Name</label>
                    <Input
                      value={form.name}
                      onChange={(e) => updateForm("name", e.target.value)}
                      placeholder="e.g. Literature Reviewer"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Visibility</label>
                    <div className="flex items-center gap-2 mt-2">
                      <button
                        type="button"
                        onClick={() => updateForm("is_public", false)}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-sm border ${
                          !form.is_public
                            ? "bg-primary text-primary-foreground border-primary"
                            : "border-muted-foreground/20"
                        }`}
                      >
                        <Lock className="h-3 w-3" /> Private
                      </button>
                      <button
                        type="button"
                        onClick={() => updateForm("is_public", true)}
                        className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-sm border ${
                          form.is_public
                            ? "bg-primary text-primary-foreground border-primary"
                            : "border-muted-foreground/20"
                        }`}
                      >
                        <Globe className="h-3 w-3" /> Public
                      </button>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium">Description</label>
                  <Input
                    value={form.description}
                    onChange={(e) => updateForm("description", e.target.value)}
                    placeholder="What does this skill help with?"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium">Tags</label>
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder="e.g. research, writing, review (comma-separated)"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Prompt Template */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Prompt Template</CardTitle>
                <CardDescription>
                  Define the instructions for the agent. Use {"{{variable}}"} syntax for
                  dynamic inputs.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  value={form.prompt_template}
                  onChange={(e) => updateForm("prompt_template", e.target.value)}
                  placeholder={`You are an expert academic reviewer. 

Your task is to review the following paper:

{{paper_text}}

Provide feedback on:
1. Methodology
2. Writing quality
3. Contribution to the field`}
                  rows={12}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  Tip: Use {"{{variable_name}}"} for placeholders that will be filled at
                  runtime.
                </p>
              </CardContent>
            </Card>

            {/* Builtin Tools */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Wrench className="h-4 w-4" /> Builtin Tools
                </CardTitle>
                <CardDescription>
                  Select which built-in tools this skill can use
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {builtinTools.map((tool) => (
                    <label
                      key={tool.name}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        form.builtin_tools.includes(tool.name)
                          ? "border-primary bg-primary/5"
                          : "border-muted-foreground/20 hover:border-muted-foreground/40"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={form.builtin_tools.includes(tool.name)}
                        onChange={() => toggleBuiltinTool(tool.name)}
                        className="mt-0.5"
                      />
                      <div>
                        <span className="text-sm font-medium">{tool.name}</span>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {tool.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Schemas */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Input / Output Schema</CardTitle>
                <CardDescription>
                  Optionally define JSON schemas for structured input and output
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Input Schema (JSON)</label>
                  <Textarea
                    value={form.input_schema}
                    onChange={(e) => updateForm("input_schema", e.target.value)}
                    placeholder={`{
  "type": "object",
  "properties": {
    "paper_text": { "type": "string" },
    "focus_areas": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["paper_text"]
}`}
                    rows={6}
                    className="font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Output Schema (JSON)</label>
                  <Textarea
                    value={form.output_schema}
                    onChange={(e) => updateForm("output_schema", e.target.value)}
                    placeholder={`{
  "type": "object",
  "properties": {
    "summary": { "type": "string" },
    "score": { "type": "number" },
    "suggestions": { "type": "array", "items": { "type": "string" } }
  }
}`}
                    rows={6}
                    className="font-mono text-sm"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Preview */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Preview</CardTitle>
                <CardDescription>How this skill will appear to agents</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-muted rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Puzzle className="h-4 w-4 text-primary" />
                    <span className="font-medium">{form.name || "Unnamed Skill"}</span>
                    {form.is_public && (
                      <Badge variant="secondary" className="text-xs">
                        Public
                      </Badge>
                    )}
                  </div>
                  {form.description && (
                    <p className="text-sm text-muted-foreground">{form.description}</p>
                  )}
                  {form.builtin_tools.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {form.builtin_tools.map((t) => (
                        <Badge key={t} variant="outline" className="text-xs">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {form.prompt_template && (
                    <pre className="text-xs bg-background p-3 rounded-md overflow-x-auto max-h-48 whitespace-pre-wrap">
                      {form.prompt_template}
                    </pre>
                  )}
                </div>
              </CardContent>
            </Card>
          </>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <Puzzle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">Select or Create a Skill</h3>
              <p className="text-muted-foreground mb-4">
                Skills are reusable prompt templates with tools that you can assign to
                agent configs.
              </p>
              <Button onClick={handleNew}>
                <Plus className="h-4 w-4 mr-1" /> Create New Skill
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
