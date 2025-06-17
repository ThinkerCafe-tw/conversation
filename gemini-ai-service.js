// Gemini AI Service for Dating Bot
import { GoogleGenerativeAI } from '@google/generative-ai';

export class GeminiAIService {
  constructor(config) {
    this.genAI = new GoogleGenerativeAI(config.apiKey);
    this.model = this.genAI.getGenerativeModel({ model: 'gemini-pro' });
    this.visionModel = this.genAI.getGenerativeModel({ model: 'gemini-pro-vision' });
  }

  // Analyze user personality from chat history
  async analyzePersonality(chatHistory, userProfile) {
    const prompt = `
    Analyze the personality traits of this user based on their chat messages and profile:
    
    Profile:
    - Age: ${userProfile.age}
    - Bio: ${userProfile.bio}
    - Interests: ${userProfile.interests.join(', ')}
    
    Recent chat messages (最近的聊天記錄):
    ${chatHistory.slice(-50).map(msg => `${msg.timestamp}: ${msg.text}`).join('\n')}
    
    Based on this information, analyze the user's:
    1. Communication style (formal/casual/playful/professional)
    2. Emotional intelligence indicators
    3. Social preferences (extrovert/introvert/ambivert)
    4. Interests depth and passion level
    5. Humor style and personality quirks
    6. Relationship readiness indicators
    7. Cultural background influences
    
    Return a comprehensive personality analysis in JSON format:
    {
      "communicationStyle": {
        "formality": "casual|formal|mixed",
        "responsiveness": "quick|moderate|slow",
        "expressiveness": "high|medium|low",
        "emojiUsage": "frequent|moderate|rare"
      },
      "personalityTraits": {
        "extraversion": 0-100,
        "openness": 0-100,
        "conscientiousness": 0-100,
        "agreeableness": 0-100,
        "emotionalStability": 0-100
      },
      "interests": [
        {
          "category": "hobby|lifestyle|career|social",
          "name": "interest_name",
          "passionLevel": 0-100,
          "socialAspect": 0-100
        }
      ],
      "relationshipIndicators": {
        "commitment": "high|medium|low",
        "emotionalAvailability": "high|medium|low",
        "conflictStyle": "direct|harmonious|avoidant"
      },
      "conversationStyle": {
        "topicPreference": ["deep|light|mixed"],
        "questionAsking": "high|medium|low",
        "sharingLevel": "open|selective|private"
      },
      "culturalContext": {
        "communicationDirectness": "direct|indirect|mixed",
        "traditionalValues": "high|medium|low",
        "modernValues": "high|medium|low"
      }
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return JSON.parse(response.text());
    } catch (error) {
      console.error('Error analyzing personality:', error);
      return this.getDefaultPersonalityProfile();
    }
  }

  // Calculate compatibility between two users
  async calculateCompatibility(user1, user2, sharedContext = {}) {
    const prompt = `
    Calculate dating compatibility between two users considering East Asian dating culture:
    
    User 1:
    - Age: ${user1.age}, Gender: ${user1.gender}
    - Bio: ${user1.bio}
    - Interests: ${user1.interests.join(', ')}
    - Personality: ${JSON.stringify(user1.personalityTraits)}
    - Communication style: ${JSON.stringify(user1.communicationStyle)}
    
    User 2:
    - Age: ${user2.age}, Gender: ${user2.gender}
    - Bio: ${user2.bio}
    - Interests: ${user2.interests.join(', ')}
    - Personality: ${JSON.stringify(user2.personalityTraits)}
    - Communication style: ${JSON.stringify(user2.communicationStyle)}
    
    Shared context:
    - Distance: ${sharedContext.distance}km
    - Shared interests: ${sharedContext.sharedInterests?.join(', ') || 'None'}
    - Shared communities: ${sharedContext.sharedCommunities?.join(', ') || 'None'}
    
    Analysis criteria (consider East Asian dating preferences):
    1. Personality compatibility (35%)
       - Communication style match
       - Emotional stability compatibility
       - Social energy balance (introvert/extrovert)
       
    2. Shared interests and lifestyle (30%)
       - Hobby overlap and complementarity
       - Life pace and activity preferences
       - Future goal alignment
       
    3. Values and relationship approach (25%)
       - Commitment style compatibility
       - Traditional vs modern values balance
       - Family orientation
       
    4. Practical compatibility (10%)
       - Age appropriateness for the culture
       - Geographic proximity
       - Communication frequency match
    
    Return detailed analysis in JSON:
    {
      "overallScore": 0-100,
      "compatibilityBreakdown": {
        "personality": {
          "score": 0-100,
          "highlights": ["strength1", "strength2"],
          "considerations": ["consideration1", "consideration2"]
        },
        "lifestyle": {
          "score": 0-100,
          "sharedActivities": ["activity1", "activity2"],
          "complementaryAspects": ["aspect1", "aspect2"]
        },
        "values": {
          "score": 0-100,
          "alignments": ["alignment1", "alignment2"],
          "differences": ["difference1", "difference2"]
        },
        "practical": {
          "score": 0-100,
          "advantages": ["advantage1"],
          "challenges": ["challenge1"]
        }
      },
      "relationshipPrediction": {
        "communicationCompatibility": "excellent|good|moderate|challenging",
        "conflictResolutionStyle": "harmonious|complementary|requires_work",
        "longTermPotential": "high|medium|low",
        "growthAreas": ["area1", "area2"]
      },
      "recommendationReason": "Brief explanation of why they're a good match",
      "conversationTopics": ["topic1", "topic2", "topic3"],
      "dateIdeas": ["idea1", "idea2", "idea3"]
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return JSON.parse(response.text());
    } catch (error) {
      console.error('Error calculating compatibility:', error);
      return this.getDefaultCompatibilityScore();
    }
  }

  // Generate personalized conversation starters
  async generateConversationStarters(user1, user2, matchContext) {
    const prompt = `
    Create personalized conversation starters for a new dating match on a LINE bot platform.
    
    User 1 Profile:
    - Name: ${user1.displayName}
    - Age: ${user1.age}
    - Interests: ${user1.interests.join(', ')}
    - Bio: ${user1.bio}
    - Personality style: ${user1.communicationStyle?.formality || 'casual'}
    
    User 2 Profile:
    - Name: ${user2.displayName}
    - Age: ${user2.age}
    - Interests: ${user2.interests.join(', ')}
    - Bio: ${user2.bio}
    
    Match Context:
    - Shared interests: ${matchContext.sharedInterests?.join(', ') || 'None'}
    - Compatibility reason: ${matchContext.compatibilityReason}
    - Match score: ${matchContext.score}/100
    
    Create 5 conversation starters that are:
    1. Personalized to their shared interests or complementary traits
    2. Culturally appropriate for East Asian dating context
    3. Engaging but not too forward or aggressive
    4. Open-ended to encourage meaningful responses
    5. Natural and not overly scripted
    6. Suitable for LINE chat format (not too long)
    
    Categories to include:
    - 1 based on shared interests
    - 1 about their photos/bio
    - 1 lifestyle/activity related
    - 1 light and fun
    - 1 thoughtful/deeper
    
    Return as JSON array with categorized starters:
    {
      "starters": [
        {
          "category": "shared_interest",
          "text": "Conversation starter text",
          "reasoning": "Why this starter works for them",
          "expectedResponse": "Type of response this might generate"
        }
      ]
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const parsed = JSON.parse(response.text());
      return parsed.starters || [];
    } catch (error) {
      console.error('Error generating conversation starters:', error);
      return this.getDefaultConversationStarters(user1, user2);
    }
  }

  // Analyze and improve user profile
  async analyzeProfileOptimization(userProfile, performanceMetrics) {
    const prompt = `
    Analyze this dating profile and suggest improvements based on performance metrics:
    
    Current Profile:
    - Bio: ${userProfile.bio}
    - Interests: ${userProfile.interests.join(', ')}
    - Photos: ${userProfile.photos.length} photos
    
    Performance Metrics:
    - Like rate: ${performanceMetrics.likeRate}%
    - Match rate: ${performanceMetrics.matchRate}%
    - Conversation rate: ${performanceMetrics.conversationRate}%
    - Profile views: ${performanceMetrics.profileViews}
    - Days active: ${performanceMetrics.daysActive}
    
    Provide specific, actionable advice to improve profile attractiveness:
    
    Return JSON with optimization suggestions:
    {
      "overallAssessment": "Profile strength assessment",
      "bioSuggestions": {
        "currentIssues": ["issue1", "issue2"],
        "improvements": ["suggestion1", "suggestion2"],
        "rewriteSuggestions": ["option1", "option2"]
      },
      "interestOptimization": {
        "addRecommendations": ["interest1", "interest2"],
        "removeRecommendations": ["interest1", "interest2"],
        "reasoning": "Why these changes would help"
      },
      "photoGuidance": {
        "currentPhotosAssessment": "Assessment of existing photos",
        "missingPhotoTypes": ["type1", "type2"],
        "photoTips": ["tip1", "tip2"]
      },
      "conversationOptimization": {
        "responseRateIssues": ["issue1", "issue2"],
        "improvementTips": ["tip1", "tip2"]
      },
      "priorityActions": ["action1", "action2", "action3"]
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return JSON.parse(response.text());
    } catch (error) {
      console.error('Error analyzing profile optimization:', error);
      return this.getDefaultProfileOptimization();
    }
  }

  // Photo analysis and verification
  async analyzePhoto(imageBuffer, photoType = 'profile') {
    const prompt = `
    Analyze this photo for a dating profile. Assess:
    
    1. Photo quality and clarity
    2. Facial visibility and lighting
    3. Background appropriateness
    4. Overall attractiveness for dating context
    5. Authenticity indicators
    6. Cultural appropriateness
    
    Photo type: ${photoType}
    
    Return analysis in JSON:
    {
      "quality": {
        "clarity": 0-100,
        "lighting": 0-100,
        "composition": 0-100
      },
      "appropriateness": {
        "datingProfile": 0-100,
        "cultural": 0-100,
        "professional": 0-100
      },
      "authenticity": {
        "likelihood": 0-100,
        "concerns": ["concern1", "concern2"]
      },
      "recommendations": ["tip1", "tip2"],
      "approved": true/false,
      "reasoning": "Brief explanation"
    }
    `;

    try {
      const imagePart = {
        inlineData: {
          data: imageBuffer.toString('base64'),
          mimeType: 'image/jpeg'
        }
      };

      const result = await this.visionModel.generateContent([prompt, imagePart]);
      const response = await result.response;
      return JSON.parse(response.text());
    } catch (error) {
      console.error('Error analyzing photo:', error);
      return { approved: true, quality: { clarity: 70, lighting: 70, composition: 70 } };
    }
  }

  // Smart reply suggestions during conversations
  async generateSmartReplies(conversationHistory, userPersonality, matchPersonality) {
    const lastMessage = conversationHistory[conversationHistory.length - 1];
    
    const prompt = `
    Generate smart reply suggestions for this dating conversation:
    
    Last message from match: "${lastMessage.text}"
    
    User personality: ${JSON.stringify(userPersonality)}
    Match personality: ${JSON.stringify(matchPersonality)}
    
    Conversation context (last 5 messages):
    ${conversationHistory.slice(-5).map(msg => 
      `${msg.sender}: ${msg.text}`
    ).join('\n')}
    
    Generate 3 reply options that are:
    1. Personality-appropriate for the user
    2. Engaging and continue the conversation
    3. Culturally appropriate
    4. Match the conversation tone
    5. Not too long for mobile chat
    
    Return JSON:
    {
      "replies": [
        {
          "text": "Reply text",
          "tone": "playful|thoughtful|enthusiastic|romantic",
          "reasoning": "Why this reply fits"
        }
      ]
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const parsed = JSON.parse(response.text());
      return parsed.replies || [];
    } catch (error) {
      console.error('Error generating smart replies:', error);
      return [];
    }
  }

  // Analyze conversation quality and provide coaching
  async analyzeConversationQuality(conversationHistory, relationshipGoals) {
    const prompt = `
    Analyze the quality of this dating conversation and provide coaching advice:
    
    Conversation history (${conversationHistory.length} messages):
    ${conversationHistory.map(msg => 
      `${msg.sender} [${msg.timestamp}]: ${msg.text}`
    ).join('\n')}
    
    Relationship goals: ${relationshipGoals}
    
    Analyze:
    1. Conversation engagement level
    2. Mutual interest indicators
    3. Communication style compatibility
    4. Red flags or concerning patterns
    5. Relationship progression potential
    6. Conversation balance (who's driving vs responding)
    
    Return coaching analysis in JSON:
    {
      "qualityScore": 0-100,
      "engagementLevel": "high|medium|low",
      "mutualInterest": {
        "userInterest": 0-100,
        "matchInterest": 0-100,
        "indicators": ["indicator1", "indicator2"]
      },
      "conversationHealth": {
        "balance": "balanced|user_dominated|match_dominated",
        "depth": "superficial|moderate|deep",
        "flow": "natural|forced|awkward"
      },
      "positiveSignals": ["signal1", "signal2"],
      "concerns": ["concern1", "concern2"],
      "coachingAdvice": {
        "nextSteps": ["step1", "step2"],
        "conversationTips": ["tip1", "tip2"],
        "topicSuggestions": ["topic1", "topic2"]
      },
      "relationshipPotential": "high|medium|low",
      "recommendedActions": ["action1", "action2"]
    }
    `;

    try {
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      return JSON.parse(response.text());
    } catch (error) {
      console.error('Error analyzing conversation quality:', error);
      return this.getDefaultConversationAnalysis();
    }
  }

  // Default fallback responses
  getDefaultPersonalityProfile() {
    return {
      communicationStyle: {
        formality: 'casual',
        responsiveness: 'moderate',
        expressiveness: 'medium',
        emojiUsage: 'moderate'
      },
      personalityTraits: {
        extraversion: 50,
        openness: 60,
        conscientiousness: 55,
        agreeableness: 65,
        emotionalStability: 60
      },
      interests: [],
      relationshipIndicators: {
        commitment: 'medium',
        emotionalAvailability: 'medium',
        conflictStyle: 'harmonious'
      }
    };
  }

  getDefaultCompatibilityScore() {
    return {
      overallScore: 70,
      compatibilityBreakdown: {
        personality: { score: 70, highlights: ['Similar communication styles'], considerations: [] },
        lifestyle: { score: 65, sharedActivities: [], complementaryAspects: [] },
        values: { score: 75, alignments: [], differences: [] },
        practical: { score: 80, advantages: [], challenges: [] }
      },
      recommendationReason: '良好的整體相容性',
      conversationTopics: ['共同興趣', '生活經驗', '未來計劃'],
      dateIdeas: ['咖啡廳聊天', '散步', '美食探索']
    };
  }

  getDefaultConversationStarters(user1, user2) {
    return [
      {
        category: 'general',
        text: `Hi ${user2.displayName}! 看到我們有共同興趣，很開心認識你 😊`,
        reasoning: 'Friendly and culturally appropriate opening'
      }
    ];
  }

  getDefaultProfileOptimization() {
    return {
      overallAssessment: '個人檔案有改善空間',
      bioSuggestions: {
        improvements: ['添加更多個人特色', '展現真實個性'],
        rewriteSuggestions: []
      },
      priorityActions: ['優化照片', '豐富自我介紹', '增加活躍度']
    };
  }

  getDefaultConversationAnalysis() {
    return {
      qualityScore: 60,
      engagementLevel: 'medium',
      conversationHealth: { balance: 'balanced', depth: 'moderate', flow: 'natural' },
      coachingAdvice: {
        nextSteps: ['Continue the conversation naturally'],
        conversationTips: ['Ask open-ended questions']
      }
    };
  }
}

// Helper functions for prompt engineering
export const PromptTemplates = {
  // Cultural context prompts for East Asian dating
  CULTURAL_CONTEXT: `
    Consider East Asian dating culture context:
    - Emphasis on stability and long-term relationships
    - Family orientation importance
    - Educational and career achievement respect
    - Polite and respectful communication style
    - Group harmony and conflict avoidance
    - Traditional and modern values balance
  `,

  // Safety and appropriateness guidelines
  SAFETY_GUIDELINES: `
    Ensure all responses are:
    - Respectful and appropriate for all audiences
    - Free from discriminatory content
    - Promoting healthy relationship dynamics
    - Culturally sensitive and inclusive
    - Privacy-conscious and secure
  `
};