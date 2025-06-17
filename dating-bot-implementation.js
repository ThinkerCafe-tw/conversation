// AI-Enhanced Dating Bot Implementation for LINE

import { Client } from '@line/bot-sdk';
import { Neo4jService } from './services/neo4j.service';
import { GeminiAIService } from './services/gemini.service';
import { FirestoreService } from './services/firestore.service';
import { RedisService } from './services/redis.service';

// Main Dating Bot Class
export class DatingBot {
  constructor(config) {
    this.lineClient = new Client(config.line);
    this.neo4j = new Neo4jService(config.neo4j);
    this.gemini = new GeminiAIService(config.gemini);
    this.firestore = new FirestoreService(config.firestore);
    this.redis = new RedisService(config.redis);
    
    this.userStates = new Map();
    this.messageHandlers = {
      ONBOARDING: this.handleOnboarding.bind(this),
      BROWSING: this.handleBrowsing.bind(this),
      MATCHING: this.handleMatching.bind(this),
      CHATTING: this.handleChatting.bind(this),
      SETTINGS: this.handleSettings.bind(this)
    };
  }

  // Main webhook handler
  async handleWebhook(event) {
    if (event.type !== 'message' && event.type !== 'postback') {
      return null;
    }

    const userId = event.source.userId;
    const userState = await this.getUserState(userId);

    try {
      const handler = this.messageHandlers[userState.flow] || this.handleMainMenu.bind(this);
      return await handler(event, userState);
    } catch (error) {
      console.error('Error handling message:', error);
      return this.sendErrorMessage(event.replyToken);
    }
  }

  // User state management
  async getUserState(userId) {
    let state = await this.redis.get(`userState:${userId}`);
    
    if (!state) {
      const userExists = await this.firestore.userExists(userId);
      state = {
        flow: userExists ? 'MAIN_MENU' : 'ONBOARDING',
        step: 0,
        data: {}
      };
    }
    
    return state;
  }

  async updateUserState(userId, state) {
    await this.redis.setex(`userState:${userId}`, 3600, JSON.stringify(state));
  }

  // Onboarding flow
  async handleOnboarding(event, state) {
    const userId = event.source.userId;
    const steps = ['welcome', 'profile', 'photos', 'interests', 'preferences', 'complete'];
    
    switch (steps[state.step]) {
      case 'welcome':
        await this.sendWelcomeMessage(event.replyToken);
        state.step++;
        break;
        
      case 'profile':
        if (event.type === 'message') {
          state.data.profile = await this.parseProfileInput(event.message.text);
          await this.sendPhotoRequest(event.replyToken);
          state.step++;
        }
        break;
        
      case 'photos':
        if (event.message?.type === 'image') {
          state.data.photos = state.data.photos || [];
          const photoUrl = await this.saveUserPhoto(userId, event.message.id);
          state.data.photos.push(photoUrl);
          
          if (state.data.photos.length < 3) {
            await this.requestMorePhotos(event.replyToken, state.data.photos.length);
          } else {
            await this.sendInterestsPrompt(event.replyToken);
            state.step++;
          }
        }
        break;
        
      case 'interests':
        if (event.type === 'postback') {
          state.data.interests = JSON.parse(event.postback.data).interests;
          await this.sendPreferencesPrompt(event.replyToken);
          state.step++;
        }
        break;
        
      case 'preferences':
        if (event.type === 'postback') {
          state.data.preferences = JSON.parse(event.postback.data).preferences;
          await this.completeOnboarding(userId, state.data);
          state.flow = 'BROWSING';
          state.step = 0;
        }
        break;
    }
    
    await this.updateUserState(userId, state);
  }

  // Main matching flow
  async handleBrowsing(event, state) {
    const userId = event.source.userId;
    
    if (event.type === 'postback') {
      const data = JSON.parse(event.postback.data);
      
      switch (data.action) {
        case 'like':
        case 'superlike':
          await this.handleLike(userId, data.targetUserId, data.action === 'superlike');
          break;
          
        case 'pass':
          await this.handlePass(userId, data.targetUserId);
          break;
          
        case 'viewMatches':
          state.flow = 'MATCHING';
          await this.showMatches(event.replyToken, userId);
          break;
          
        case 'settings':
          state.flow = 'SETTINGS';
          await this.showSettings(event.replyToken, userId);
          break;
      }
    }
    
    // Show next profile
    await this.showNextProfile(event.replyToken, userId);
    await this.updateUserState(userId, state);
  }

  // Matching logic
  async handleLike(userId, targetUserId, isSuperLike = false) {
    // Check daily quota
    const quotaKey = `quota:${userId}:${new Date().toISOString().split('T')[0]}`;
    const remainingLikes = await this.redis.get(quotaKey) || 20;
    
    if (remainingLikes <= 0 && !isSuperLike) {
      throw new Error('Daily like limit reached');
    }
    
    // Record the like in Neo4j
    const matchResult = await this.neo4j.run(`
      MATCH (u:User {lineUserId: $userId})
      MATCH (target:User {lineUserId: $targetUserId})
      CREATE (u)-[:LIKES {timestamp: datetime(), superLike: $isSuperLike}]->(target)
      
      // Check for mutual like
      WITH u, target
      OPTIONAL MATCH (target)-[:LIKES]->(u)
      WITH u, target, COUNT(*) as mutualLike
      
      // Create match if mutual
      FOREACH (_ IN CASE WHEN mutualLike > 0 THEN [1] ELSE [] END |
        CREATE (u)-[:MATCHES {timestamp: datetime()}]->(target)
        CREATE (target)-[:MATCHES {timestamp: datetime()}]->(u)
      )
      
      RETURN mutualLike > 0 as isMatch
    `, { userId, targetUserId, isSuperLike });
    
    // Update quota
    if (!isSuperLike) {
      await this.redis.setex(quotaKey, 86400, remainingLikes - 1);
    }
    
    // If it's a match, notify both users
    if (matchResult.records[0].get('isMatch')) {
      await this.notifyMatch(userId, targetUserId);
    }
    
    // If super like, notify target
    if (isSuperLike) {
      await this.notifySuperLike(targetUserId, userId);
    }
  }

  // AI-powered profile display
  async showNextProfile(replyToken, userId) {
    // Get recommendations from cache or generate new ones
    let recommendations = await this.redis.get(`recommendations:${userId}`);
    
    if (!recommendations) {
      recommendations = await this.generateRecommendations(userId);
    }
    
    if (recommendations.length === 0) {
      return this.sendNoMoreProfiles(replyToken);
    }
    
    const profile = recommendations[0];
    const aiInsights = await this.getAIInsights(userId, profile.userId);
    
    // Create rich profile card
    const profileCard = this.createProfileCard(profile, aiInsights);
    
    await this.lineClient.replyMessage(replyToken, profileCard);
    
    // Update cache
    await this.redis.setex(
      `recommendations:${userId}`,
      3600,
      JSON.stringify(recommendations.slice(1))
    );
  }

  // AI recommendation engine
  async generateRecommendations(userId) {
    const user = await this.firestore.getUser(userId);
    
    // Get potential matches from Neo4j
    const candidates = await this.neo4j.run(`
      MATCH (u:User {lineUserId: $userId})
      MATCH (candidate:User)
      WHERE candidate.lineUserId <> $userId
        AND candidate.age >= $minAge 
        AND candidate.age <= $maxAge
        AND NOT (u)-[:LIKES|BLOCKS|MATCHES]-(candidate)
        AND distance(u.location, candidate.location) <= $maxDistance * 1000
      
      WITH u, candidate, distance(u.location, candidate.location) / 1000 as distanceKm
      
      // Get shared interests
      OPTIONAL MATCH (u)-[:HAS_INTEREST]->(interest)<-[:HAS_INTEREST]-(candidate)
      WITH u, candidate, distanceKm, COLLECT(DISTINCT interest.name) as sharedInterests
      
      // Get shared communities
      OPTIONAL MATCH (u)-[:IN_COMMUNITY]->(community)<-[:IN_COMMUNITY]-(candidate)
      WITH u, candidate, distanceKm, sharedInterests, COLLECT(DISTINCT community.name) as sharedCommunities
      
      RETURN candidate {
        .*, 
        distance: distanceKm,
        sharedInterests: sharedInterests,
        sharedCommunities: sharedCommunities
      }
      ORDER BY SIZE(sharedInterests) DESC, distanceKm ASC
      LIMIT 50
    `, {
      userId,
      minAge: user.preferences.ageRange.min,
      maxAge: user.preferences.ageRange.max,
      maxDistance: user.preferences.maxDistance
    });
    
    // Score each candidate with AI
    const scoredCandidates = await Promise.all(
      candidates.records.map(async (record) => {
        const candidate = record.get('candidate');
        const compatibility = await this.calculateAICompatibility(user, candidate);
        
        return {
          ...candidate,
          compatibilityScore: compatibility.score,
          compatibilityReasons: compatibility.reasons,
          conversationStarters: await this.generateConversationStarters(user, candidate)
        };
      })
    );
    
    // Sort by compatibility score
    return scoredCandidates.sort((a, b) => b.compatibilityScore - a.compatibilityScore);
  }

  // AI compatibility calculation
  async calculateAICompatibility(user1, user2) {
    const prompt = `
    Analyze compatibility between two users for dating:
    
    User 1:
    - Interests: ${user1.interests.join(', ')}
    - Bio: ${user1.bio}
    - Age: ${user1.age}
    - Personality indicators: ${JSON.stringify(user1.personalityTraits)}
    
    User 2:
    - Interests: ${user2.interests.join(', ')}
    - Bio: ${user2.bio}
    - Age: ${user2.age}
    - Shared interests: ${user2.sharedInterests.join(', ')}
    - Distance: ${user2.distance}km
    
    Calculate a compatibility score (0-100) based on:
    1. Shared interests and hobbies (40%)
    2. Personality compatibility (30%)
    3. Life stage alignment (20%)
    4. Geographic proximity (10%)
    
    Return JSON:
    {
      "score": number,
      "reasons": ["reason1", "reason2", "reason3"],
      "strengths": ["strength1", "strength2"],
      "considerations": ["consideration1", "consideration2"]
    }
    `;
    
    const response = await this.gemini.generateJSON(prompt);
    return response;
  }

  // Generate AI conversation starters
  async generateConversationStarters(user1, user2) {
    const prompt = `
    Create 3 personalized conversation starters for a dating match:
    
    Person 1 interests: ${user1.interests.join(', ')}
    Person 2 interests: ${user2.interests.join(', ')}
    Shared interests: ${user2.sharedInterests.join(', ')}
    
    Guidelines:
    - Make them engaging and specific to shared interests
    - Avoid generic greetings
    - Include open-ended questions
    - Keep them casual and friendly
    - Consider cultural context (East Asian dating culture)
    
    Return as JSON array of strings.
    `;
    
    const response = await this.gemini.generateJSON(prompt);
    return response;
  }

  // Create rich profile card for LINE
  createProfileCard(profile, aiInsights) {
    return {
      type: 'flex',
      altText: `${profile.displayName} - ${profile.age}歲`,
      contents: {
        type: 'carousel',
        contents: [
          // Main profile bubble
          {
            type: 'bubble',
            hero: {
              type: 'image',
              url: profile.photos[0],
              size: 'full',
              aspectRatio: '3:4',
              aspectMode: 'cover'
            },
            body: {
              type: 'box',
              layout: 'vertical',
              spacing: 'md',
              contents: [
                {
                  type: 'text',
                  text: `${profile.displayName}, ${profile.age}`,
                  size: 'xl',
                  weight: 'bold'
                },
                {
                  type: 'text',
                  text: `📍 ${Math.round(profile.distance)}km away`,
                  size: 'sm',
                  color: '#999999'
                },
                {
                  type: 'text',
                  text: profile.bio,
                  wrap: true,
                  size: 'sm',
                  margin: 'md'
                },
                {
                  type: 'box',
                  layout: 'baseline',
                  spacing: 'xs',
                  contents: [
                    {
                      type: 'text',
                      text: '💫 AI相容度',
                      size: 'xs',
                      color: '#0084ff',
                      flex: 0
                    },
                    {
                      type: 'text',
                      text: `${aiInsights.compatibilityScore}%`,
                      size: 'xs',
                      color: '#0084ff',
                      weight: 'bold'
                    }
                  ]
                },
                {
                  type: 'separator',
                  margin: 'md'
                },
                {
                  type: 'box',
                  layout: 'horizontal',
                  spacing: 'xs',
                  contents: profile.sharedInterests.slice(0, 3).map(interest => ({
                    type: 'box',
                    layout: 'baseline',
                    contents: [
                      {
                        type: 'text',
                        text: `#${interest}`,
                        size: 'xs',
                        color: '#905c44',
                        flex: 0
                      }
                    ],
                    borderWidth: '1px',
                    borderColor: '#905c44',
                    cornerRadius: '12px',
                    paddingAll: 'xs'
                  }))
                }
              ]
            },
            footer: {
              type: 'box',
              layout: 'horizontal',
              spacing: 'sm',
              contents: [
                {
                  type: 'button',
                  action: {
                    type: 'postback',
                    label: '❌',
                    data: JSON.stringify({
                      action: 'pass',
                      targetUserId: profile.lineUserId
                    })
                  },
                  style: 'secondary',
                  height: 'sm'
                },
                {
                  type: 'button',
                  action: {
                    type: 'postback',
                    label: '💚 喜歡',
                    data: JSON.stringify({
                      action: 'like',
                      targetUserId: profile.lineUserId
                    })
                  },
                  style: 'primary',
                  height: 'sm',
                  flex: 2
                },
                {
                  type: 'button',
                  action: {
                    type: 'postback',
                    label: '⭐',
                    data: JSON.stringify({
                      action: 'superlike',
                      targetUserId: profile.lineUserId
                    })
                  },
                  style: 'secondary',
                  height: 'sm'
                }
              ]
            }
          },
          // Additional photos bubble
          ...profile.photos.slice(1, 3).map(photo => ({
            type: 'bubble',
            hero: {
              type: 'image',
              url: photo,
              size: 'full',
              aspectRatio: '3:4',
              aspectMode: 'cover'
            }
          })),
          // AI insights bubble
          {
            type: 'bubble',
            body: {
              type: 'box',
              layout: 'vertical',
              spacing: 'md',
              contents: [
                {
                  type: 'text',
                  text: '💫 AI 分析洞察',
                  size: 'lg',
                  weight: 'bold',
                  color: '#0084ff'
                },
                {
                  type: 'separator',
                  margin: 'md'
                },
                {
                  type: 'text',
                  text: '為什麼你們很相配：',
                  size: 'sm',
                  weight: 'bold',
                  margin: 'md'
                },
                ...aiInsights.compatibilityReasons.map(reason => ({
                  type: 'text',
                  text: `• ${reason}`,
                  size: 'xs',
                  wrap: true,
                  margin: 'sm'
                })),
                {
                  type: 'text',
                  text: '建議的開場白：',
                  size: 'sm',
                  weight: 'bold',
                  margin: 'lg'
                },
                ...aiInsights.conversationStarters.slice(0, 2).map((starter, idx) => ({
                  type: 'box',
                  layout: 'baseline',
                  margin: 'sm',
                  contents: [
                    {
                      type: 'text',
                      text: `${idx + 1}.`,
                      size: 'xs',
                      flex: 0
                    },
                    {
                      type: 'text',
                      text: starter,
                      size: 'xs',
                      wrap: true,
                      flex: 1
                    }
                  ]
                }))
              ]
            }
          }
        ]
      }
    };
  }

  // Match notification
  async notifyMatch(userId1, userId2) {
    const [user1, user2] = await Promise.all([
      this.firestore.getUser(userId1),
      this.firestore.getUser(userId2)
    ]);
    
    const matchMessage = {
      type: 'flex',
      altText: '🎉 新的配對！',
      contents: {
        type: 'bubble',
        hero: {
          type: 'box',
          layout: 'horizontal',
          contents: [
            {
              type: 'image',
              url: user2.photos[0],
              size: 'full',
              aspectMode: 'cover',
              flex: 1
            },
            {
              type: 'box',
              layout: 'vertical',
              contents: [
                {
                  type: 'text',
                  text: '🎉',
                  size: 'xxl',
                  align: 'center'
                }
              ],
              justifyContent: 'center',
              alignItems: 'center',
              flex: 1,
              backgroundColor: '#FF6B6B'
            },
            {
              type: 'image',
              url: user1.photos[0],
              size: 'full',
              aspectMode: 'cover',
              flex: 1
            }
          ],
          aspectRatio: '3:1',
          aspectMode: 'cover'
        },
        body: {
          type: 'box',
          layout: 'vertical',
          spacing: 'md',
          contents: [
            {
              type: 'text',
              text: '恭喜配對成功！',
              size: 'xl',
              weight: 'bold',
              align: 'center'
            },
            {
              type: 'text',
              text: `你和 ${user2.displayName} 互相喜歡對方`,
              size: 'sm',
              align: 'center',
              wrap: true
            },
            {
              type: 'separator',
              margin: 'lg'
            },
            {
              type: 'text',
              text: 'AI 建議的開場白：',
              size: 'sm',
              weight: 'bold'
            },
            {
              type: 'text',
              text: user2.conversationStarters[0],
              size: 'xs',
              wrap: true,
              margin: 'sm'
            }
          ]
        },
        footer: {
          type: 'box',
          layout: 'vertical',
          spacing: 'sm',
          contents: [
            {
              type: 'button',
              action: {
                type: 'postback',
                label: '開始聊天',
                data: JSON.stringify({
                  action: 'startChat',
                  matchUserId: userId2
                })
              },
              style: 'primary'
            }
          ]
        }
      }
    };
    
    await this.lineClient.pushMessage(userId1, matchMessage);
    
    // Send similar message to user2
    const reciprocalMessage = { ...matchMessage };
    reciprocalMessage.contents.body.contents[1].text = `你和 ${user1.displayName} 互相喜歡對方`;
    reciprocalMessage.contents.footer.contents[0].action.data = JSON.stringify({
      action: 'startChat',
      matchUserId: userId1
    });
    
    await this.lineClient.pushMessage(userId2, reciprocalMessage);
  }
}

// Export main handler
export const handleDatingWebhook = async (req, res) => {
  const bot = new DatingBot({
    line: {
      channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN,
      channelSecret: process.env.LINE_CHANNEL_SECRET
    },
    neo4j: {
      uri: process.env.NEO4J_URI,
      user: process.env.NEO4J_USER,
      password: process.env.NEO4J_PASSWORD
    },
    gemini: {
      apiKey: process.env.GEMINI_API_KEY
    },
    firestore: {
      // Firestore config
    },
    redis: {
      host: process.env.REDIS_HOST,
      port: process.env.REDIS_PORT,
      password: process.env.REDIS_PASSWORD
    }
  });
  
  const events = req.body.events;
  
  await Promise.all(events.map(event => bot.handleWebhook(event)));
  
  res.status(200).json({ success: true });
};