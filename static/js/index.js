// index.js - Main page script for document handling

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileUpload = document.getElementById('file-upload');
    const uploadButton = document.getElementById('upload-button');
    const loadingSpinner = document.getElementById('loading-spinner');
    const uploadStatus = document.getElementById('upload-status');
    const resultContainer = document.getElementById('result-container');
    const explanationText = document.getElementById('explanation-text');
    const explanationAudio = document.getElementById('explanation-audio');
    const rawText = document.getElementById('raw-text');
    const quizContainer = document.getElementById('quiz-container');
    const checkAnswersBtn = document.getElementById('check-answers');
    const newQuestionsBtn = document.getElementById('new-questions');
    const quizLoadingSpinner = document.getElementById('quiz-loading');

    // Quiz options selectors
    const difficultySelect = document.getElementById('difficulty');
    const taxonomySelect = document.getElementById('taxonomy');
    const formatSelect = document.getElementById('format');

    let currentQuiz = [];
    let extractedText = '';
    let quizAnswers = [];
    
    // Check if we have data in session (returning from avatar page)
    checkSessionData();
    
    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!fileUpload.files[0]) {
            showUploadStatus('Please select a file to upload.', 'alert-warning');
            return;
        }
        
        const file = fileUpload.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        startLoading();
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Upload failed');
                });
            }
            return response.json();
        })
        .then(data => {
            stopLoading();
            displayResults(data);
        })
        .catch(error => {
            stopLoading();
            showUploadStatus(error.message, 'alert-danger');
        });
    });
    
    // Function to check the session data when returning from avatar page
    function checkSessionData() {
        fetch('/get_session_data')
            .then(response => response.json())
            .then(data => {
                if (data.has_processed_file) {
                    displayResults(data);
                }
            })
            .catch(error => {
                console.error('Error checking session data:', error);
            });
    }
    
    // Function to handle loading state
    function startLoading() {
        uploadButton.disabled = true;
        loadingSpinner.style.display = 'inline-block';
        uploadButton.querySelector('span:not(#loading-spinner)') 
            ? uploadButton.querySelector('span:not(#loading-spinner)').textContent = 'Processing...'
            : uploadButton.textContent = 'Processing...';
        showUploadStatus('Uploading and analyzing your document...', 'alert-info');
    }
    
    function stopLoading() {
        uploadButton.disabled = false;
        loadingSpinner.style.display = 'none';
        uploadButton.querySelector('span:not(#loading-spinner)') 
            ? uploadButton.querySelector('span:not(#loading-spinner)').textContent = 'Analyze Document'
            : uploadButton.textContent = 'Analyze Document';
    }
    
    // Show upload status message
    function showUploadStatus(message, className) {
        uploadStatus.textContent = message;
        uploadStatus.className = `alert ${className}`;
        uploadStatus.style.display = 'block';
    }
    
    // Display results from the API
    function displayResults(data) {
        // Store the extracted text for quiz generation
        extractedText = data.extracted_text;
        
        // Display the explanation
        explanationText.textContent = data.explanation;
        
        // Set the audio file
        if (data.audio_file) {
            explanationAudio.src = data.audio_file;
        }
        
        // Display the raw text
        rawText.textContent = data.extracted_text;
        
        // Generate quiz
        try {
            currentQuiz = JSON.parse(data.quiz);
            generateQuizUI(currentQuiz);
        } catch (error) {
            console.error('Error parsing quiz JSON:', error);
            quizContainer.innerHTML = '<div class="alert alert-warning">Unable to generate quiz for this document.</div>';
        }
        
        // Show the result container
        resultContainer.style.display = 'block';
        
        // Scroll to results
        resultContainer.scrollIntoView({ behavior: 'smooth' });
    }
    
    // Generate quiz UI from quiz data
    function generateQuizUI(quizData) {
        quizContainer.innerHTML = '';
        quizAnswers = [];
        
        quizData.forEach((question, index) => {
            const questionEl = document.createElement('div');
            questionEl.className = 'quiz-question';
            
            // Create badges for difficulty, taxonomy level, and format if they exist
            let badgesHTML = '';
            if (question.difficulty) {
                const badgeClass = getBadgeClass(question.difficulty);
                badgesHTML += `<span class="badge ${badgeClass} me-2">${question.difficulty}</span>`;
            }
            
            if (question.taxonomy_level) {
                badgesHTML += `<span class="badge bg-info me-2">${question.taxonomy_level}</span>`;
            }
            
            if (question.format) {
                badgesHTML += `<span class="badge bg-primary me-2">${question.format}</span>`;
            }
            
            // Add badges to the question header if any exist
            const badgesDiv = badgesHTML ? `<div class="mb-2">${badgesHTML}</div>` : '';
            
            questionEl.innerHTML = `
                <h5>${index + 1}. ${question.question}</h5>
                ${badgesDiv}
                <div class="quiz-options" id="options-${index}"></div>
                <div class="quiz-feedback alert" id="feedback-${index}"></div>
            `;
            
            quizContainer.appendChild(questionEl);
            
            const optionsContainer = document.getElementById(`options-${index}`);
            
            // Determine the question format
            const format = question.format || 'mcq';
            
            if (format === 'true_false') {
                // True/False questions
                ['True', 'False'].forEach((option, optIndex) => {
                    createOptionElement(optionsContainer, option, index, optIndex);
                });
            } else if (format === 'short_answer') {
                // Short answer questions
                const inputGroup = document.createElement('div');
                inputGroup.className = 'input-group mb-3';
                
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control';
                input.id = `short-answer-${index}`;
                input.placeholder = 'Type your answer here';
                
                input.addEventListener('input', function() {
                    quizAnswers[index] = this.value.trim();
                });
                
                inputGroup.appendChild(input);
                optionsContainer.appendChild(inputGroup);
            } else {
                // Multiple choice questions
                question.option.forEach((option, optIndex) => {
                    createOptionElement(optionsContainer, option, index, optIndex);
                });
            }
        });
    }
    
    // Helper function to create option elements
    function createOptionElement(container, option, questionIndex, optionIndex) {
        const optionLabel = document.createElement('label');
        optionLabel.className = 'option-label';
        optionLabel.innerHTML = `
            <input type="radio" name="question-${questionIndex}" value="${option}" class="me-2">
            ${option}
        `;
        
        optionLabel.addEventListener('click', function() {
            // Remove selected class from all options in this question
            const options = container.querySelectorAll('.option-label');
            options.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to this option
            this.classList.add('selected');
            
            // Store the answer
            quizAnswers[questionIndex] = option;
        });
        
        container.appendChild(optionLabel);
    }
    
    // Helper function to get badge class based on difficulty
    function getBadgeClass(difficulty) {
        switch(difficulty.toLowerCase()) {
            case 'easy':
                return 'bg-success';
            case 'medium':
                return 'bg-warning';
            case 'hard':
                return 'bg-danger';
            default:
                return 'bg-secondary';
        }
    }
    
    // Check answers button handler
    checkAnswersBtn.addEventListener('click', function() {
        let score = 0;
        
        currentQuiz.forEach((question, index) => {
            const feedbackEl = document.getElementById(`feedback-${index}`);
            const format = question.format || 'mcq';
            let selectedOption = quizAnswers[index];
            
            // For short answer questions
            if (format === 'short_answer') {
                const inputEl = document.getElementById(`short-answer-${index}`);
                selectedOption = inputEl ? inputEl.value.trim() : '';
                
                // Check if answer is correct (case-insensitive)
                const acceptableAnswers = Array.isArray(question.option) ? question.option : [];
                const isCorrect = acceptableAnswers.some(answer => 
                    selectedOption.toLowerCase() === answer.toLowerCase());
                
                if (selectedOption) {
                    if (isCorrect) {
                        // Correct answer
                        score++;
                        feedbackEl.textContent = `Correct! ${question.explanation}`;
                        feedbackEl.className = 'quiz-feedback alert alert-success';
                        inputEl.classList.add('is-valid');
                        inputEl.classList.remove('is-invalid');
                    } else {
                        // Incorrect answer
                        feedbackEl.textContent = `Incorrect. Acceptable answers: "${question.option.join('" or "')}". ${question.explanation}`;
                        feedbackEl.className = 'quiz-feedback alert alert-danger';
                        inputEl.classList.add('is-invalid');
                        inputEl.classList.remove('is-valid');
                    }
                } else {
                    // No answer
                    feedbackEl.textContent = `You didn't answer this question. Acceptable answers: "${question.option.join('" or "')}".`;
                    feedbackEl.className = 'quiz-feedback alert alert-warning';
                }
                
                feedbackEl.style.display = 'block';
                // Remove this continue statement as it's trying to jump across function boundaries
                // continue;
            } else {
                // For MCQ and True/False questions
                const optionsContainer = document.getElementById(`options-${index}`);
                const options = optionsContainer.querySelectorAll('.option-label');
                
                // Reset classes
                options.forEach(opt => {
                    opt.classList.remove('correct', 'incorrect');
                });
                
                if (selectedOption) {
                    if (selectedOption === question.answer) {
                        // Correct answer
                        score++;
                        feedbackEl.textContent = `Correct! ${question.explanation}`;
                        feedbackEl.className = 'quiz-feedback alert alert-success';
                        feedbackEl.style.display = 'block';
                        
                        // Highlight correct answer
                        options.forEach(opt => {
                            if (opt.textContent.trim().includes(selectedOption)) {
                                opt.classList.add('correct');
                            }
                        });
                    } else {
                        // Incorrect answer
                        feedbackEl.textContent = `Incorrect. The correct answer is "${question.answer}". ${question.explanation}`;
                        feedbackEl.className = 'quiz-feedback alert alert-danger';
                        feedbackEl.style.display = 'block';
                        
                        // Highlight incorrect and correct answers
                        options.forEach(opt => {
                            if (opt.textContent.trim().includes(selectedOption)) {
                                opt.classList.add('incorrect');
                            } else if (opt.textContent.trim().includes(question.answer)) {
                                opt.classList.add('correct');
                            }
                        });
                    }
                } else {
                    // No answer selected
                    feedbackEl.textContent = `You didn't answer this question. The correct answer is "${question.answer}".`;
                    feedbackEl.className = 'quiz-feedback alert alert-warning';
                    feedbackEl.style.display = 'block';
                    
                    // Highlight correct answer
                    options.forEach(opt => {
                        if (opt.textContent.trim().includes(question.answer)) {
                            opt.classList.add('correct');
                        }
                    });
                }
            }
        });
        
        // Show overall score
        const scoreAlert = document.createElement('div');
        scoreAlert.className = 'alert alert-info mt-3';
        scoreAlert.textContent = `Your score: ${score} out of ${currentQuiz.length}`;
        quizContainer.prepend(scoreAlert);
        
        // Disable check button after submission
        this.disabled = true;
    });
    
    // Generate new questions button handler
    newQuestionsBtn.addEventListener('click', function() {
        if (!extractedText) {
            return;
        }
        
        // Get quiz options
        const difficulty = difficultySelect.value;
        const taxonomy = taxonomySelect.value;
        const format = formatSelect.value;
        
        // Get previous questions to avoid duplicates
        const previousQuestions = currentQuiz.map(q => q.question);
        
        // Show loading spinner
        quizLoadingSpinner.classList.remove('d-none');
        
        fetch('/generate_quiz', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                extracted_text: extractedText,
                previous_questions: previousQuestions,
                difficulty: difficulty,
                taxonomy: taxonomy,
                format: format
            })
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading spinner
            quizLoadingSpinner.classList.add('d-none');
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            try {
                const newQuiz = JSON.parse(data.quiz);
                currentQuiz = newQuiz;
                generateQuizUI(currentQuiz);
                
                // Enable check button again
                checkAnswersBtn.disabled = false;
                
                // Remove any existing score alert
                const oldScoreAlert = quizContainer.querySelector('.alert.alert-info.mt-3');
                if (oldScoreAlert) {
                    oldScoreAlert.remove();
                }
                
                // Scroll to quiz
                document.getElementById('quiz-tab').click();
                quizContainer.scrollIntoView({ behavior: 'smooth' });
            } catch (error) {
                console.error('Error parsing new quiz JSON:', error);
                alert('Failed to generate new questions. Please try again.');
            }
        })
        .catch(error => {
            // Hide loading spinner
            quizLoadingSpinner.classList.add('d-none');
            console.error('Error generating new quiz:', error);
            alert(error.message);
        });
    });

    // Download quiz functionality
    document.getElementById('download-quiz').addEventListener('click', function() {
        if (!currentQuiz.length) {
            alert("No quiz available to download.");
            return;
        }

        let quizText = "AI Quiz with Answers and Explanations\n\n";

        currentQuiz.forEach((q, idx) => {
            quizText += `${idx + 1}. ${q.question}\n`;

            if (Array.isArray(q.option)) {
                q.option.forEach((opt, i) => {
                    quizText += `   - ${opt}\n`;
                });
            }

            if (q.answer) {
                quizText += `Answer: ${q.answer}\n`;
            } else if (Array.isArray(q.option)) {
                quizText += `Acceptable Answers: ${q.option.join(' or ')}\n`;
            }

            quizText += `Explanation: ${q.explanation}\n\n`;
        });

        const blob = new Blob([quizText], { type: "text/plain;charset=utf-8" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "quiz_with_answers.txt";
        link.click();
    });
});