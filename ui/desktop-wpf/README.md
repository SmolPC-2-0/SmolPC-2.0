# LibreOfficeAI

Welcome to the **AI Assistant for LibreOffice** application.
The app integrates local AI with LibreOffice Writer and Impress. It allows you to create and edit documents and presentations using a chat interface. You can simply send it a message and it will carry out your request.

e.g. “Please create me a sales pitch presentation for the new Intel laptops”

The app also offers voice transcription using Whisper, allowing users to interact with the AI without typing. All AI models are run locally on-device, so it does not need an internet connection and keeps all data completely secure. It integrates an MCP Server which gives the AI direct access to LibreOffice functionality.

## User Manual

> **System Requirements**
> - Windows version **10.0.17763.0** or higher
> - LibreOffice installed: [Download here](https://www.libreoffice.org/download/download-libreoffice/)

---

### 🚀 Starting the Application

To launch the application, double-click `LibreOfficeAI.exe`. This opens the main window and displays a loading screen.

If the selected AI model is not found locally, it will be downloaded automatically.

Once the model is ready and LibreOffice is connected, the main page appears. The application respects system color settings and will display in Dark Mode if enabled.

---

### ✍️ Using the Application

This application connects to LibreOffice to create and edit documents and presentations based on your requests.

#### 📨 Sending a Message

You can send a message in two ways:

1. **Typing**  
   Click the textbox at the bottom of the screen and type your message.

2. **Voice Transcription**  
   Click the `Record Message` button to start recording. A red pulsating glow indicates active recording. Click again to stop.  
   You can also press the **spacebar** to start/stop recording (if the textbox is not selected).

After composing your message, click the green `Send Message` button or press **Enter**.

---

#### ❌ Cancelling a Message Request

Once a message is sent, the AI begins processing. If you wish to cancel, click the `Cancel request` button. This halts processing and lets you send a new message. The AI will not retain the cancelled request.

---

### 🧠 AI Capabilities

The AI assistant can perform a wide range of actions. Below is a complete list of supported features with example prompts.

> For unsupported or highly specific tasks, it's recommended to use LibreOffice directly.

| **Purpose** | **Example Prompt** |
|------------|--------------------|
| Look at document properties | “Can you tell me the properties of the ‘True story’ document?” |
| List all documents | “Can you list all of the available documents?” |
| Make a copy of a document | “Can you make a copy of the Sales Pitch document?” |
| Create a new document | “Can you make a new document called ‘Board Meeting’?” |
| Read contents of a document | “Can you give me a summary of the Meeting Notes document?” |
| Add text | “Can you add the sentence ‘All is fair in love and war’ to the quotes document?” |
| Add headings | “Can you add a new heading, ‘How I found my true self’, to the Meditation document?” |
| Add paragraphs | “Can you add a paragraph about dogs to the animals document?” |
| Add tables | “Can you add a table about the pros and cons of capitalism?” |
| Insert page breaks | “Insert a page break at the end of the Freedom document” |
| Format text | “Please use a bigger font for the text ‘Things can only get better’ – make it green and use the Georgia font” |
| Find and replace text | “Can you replace the phrase ‘We shouldn’t speak any more’ with ‘You know where to find me’” |
| Delete specific text | “Please delete ‘The time has come’ from the proposal document” |
| Format a table | “Please give a header row and thicker borders to the second table in the ‘Product Review’ document” |
| Delete paragraphs | “Delete the first paragraph in the ‘Bird Species’ document” |
| Apply styling to a document | “Please give the ‘Party invitation’ document a fun styling, with big colourful text” |
| Insert images into a document | “Please insert the following image into the ‘Animals’ document: C:\Users\username\Downloads\monkey.png” |
| Create a new presentation | “Can you create me a presentation called ‘Business Proposal’?” |
| Read contents of a presentation | “Can you give me a summary of the ‘Team Agenda’ presentation?” |
| Add a slide with title and content | “Can you add a slide about AI training to the Onboarding presentation?” |
| Change slide title | “Can you change the title of the second slide to ‘Supporting other team members’?” |
| Change slide content | “Can you change the content of the second slide to a list of how to support other members of your team?” |
| Delete a slide | “Delete the fourth slide” |
| Apply a presentation template | “Please apply the Blue Curve template to the Lesson Plan presentation” |
| Format slide title | “Please make the title of the first slide bold, blue and centred” |
| Format slide content | “Please make the content of the first slide smaller and in italics, with a light blue background” |
| Insert image into a slide | “Please insert this image into the 5th slide of the ‘Roadmap’ presentation: C:\Users\username\Pictures\roadmap_diagram.jpeg” |

---

### 📄 AI Response

Once your message is processed, the AI will respond. If tools are used, they will be listed at the top of the response.

If a document or presentation is created or edited, the filename will appear as a clickable link beneath the LibreOffice logo. Double-clicking the link opens the file in LibreOffice or your default editor.

---

### 🆕 Starting a New Chat

For new tasks, it's recommended to start a fresh chat using the button at the top left of the screen.

> The AI has limited memory. Long conversations may cause it to forget earlier context. Starting a new chat resets the conversation history.

---

## Build & Run Guide for LibreOfficeAI

This guide outlines the steps to compile and run the application using **Visual Studio**.

> **Prerequisites**  
> Ensure the following workloads and components are installed via Visual Studio Installer:
> - `.NET desktop development`
> - `Python development`
> - `MSVC C++ x64/x86 build tools (Latest)`

---

### 📥 1. Download the Project Files

1. Open Visual Studio.
2. Select **"Clone a repository"**.
3. Enter the repository URL (see above).
4. Click **"Clone"**.  
   Visual Studio will clone the repository and open the project.

---

### 📦 2. Include Ollama

1. Create a folder named `Ollama` in the root directory of the project.
2. Visit [Ollama Releases](https://github.com/ollama/ollama/releases).
3. Download the latest `ollama-windows-amd64.zip`.
4. Extract all contents into the `Ollama` folder.

---

### 🔊 3. Include the Whisper Model

1. Create a folder named `WhisperModels` in the root directory.
2. Download the model file from:  
   [`ggml-base.bin`](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin)
3. Place the file into the `WhisperModels` folder.

---

### 🚀 4. Publish the Project

1. In Visual Studio, right-click the `LibreOfficeAI` project in **Solution Explorer**.
2. Select **"Publish"**.
3. Choose **"Folder"** as the target and click **Next**.
4. Confirm **"Folder"** as the specific target and click **Next**.
5. Select a destination folder and click **Finish**.
6. Close the popup and click **Publish**.

---

### ▶️ 5. Run the Application

1. Navigate to the published folder.
2. Double-click `LibreOfficeAI.exe` to launch the app.

> ⚠️ **Note**  
> The `main.exe` and `libre.exe` files are compiled with **Nuitka**, which may trigger false positives in Windows Defender or other antivirus software.  
> You may need to:
> - Manually allow these files to run.
> - Remove them from quarantine if flagged.
> - Verify that both files remain in the `MCPServer` folder within the published directory if startup errors occur.

---

Feel free to open an issue if you encounter any problems or need help setting up!
