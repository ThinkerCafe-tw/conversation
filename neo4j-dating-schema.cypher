// Neo4j Dating System Schema and Setup

// Create constraints and indexes for performance
CREATE CONSTRAINT user_line_id IF NOT EXISTS ON (u:User) ASSERT u.lineUserId IS UNIQUE;
CREATE INDEX user_age IF NOT EXISTS FOR (u:User) ON (u.age);
CREATE INDEX user_location IF NOT EXISTS FOR (u:User) ON (u.location);
CREATE INDEX user_last_active IF NOT EXISTS FOR (u:User) ON (u.lastActive);
CREATE INDEX interest_name IF NOT EXISTS FOR (i:Interest) ASSERT i.name IS UNIQUE;
CREATE INDEX community_name IF NOT EXISTS FOR (c:Community) ASSERT c.name IS UNIQUE;

// User node structure
// Example: Create a user
CREATE (u:User {
  lineUserId: 'U1234567890abcdef',
  displayName: 'Alice',
  profilePicture: 'https://example.com/photo.jpg',
  bio: 'Love hiking and coffee',
  age: 28,
  gender: 'female',
  location: point({latitude: 25.0330, longitude: 121.5654}), // Taipei
  interests: ['hiking', 'coffee', 'photography'],
  personalityType: 'ENFP',
  lastActive: datetime(),
  isPremium: false,
  createdAt: datetime(),
  settings: {
    visibility: 'visible',
    notifications: true,
    ageRangeMin: 25,
    ageRangeMax: 35,
    maxDistance: 50,
    genderPreference: 'male'
  }
});

// Interest nodes - create common interests
UNWIND [
  'hiking', 'coffee', 'photography', 'cooking', 'travel',
  'music', 'movies', 'reading', 'fitness', 'art',
  'gaming', 'yoga', 'dancing', 'sports', 'technology',
  'fashion', 'food', 'nature', 'pets', 'volunteering'
] AS interestName
CREATE (i:Interest {name: interestName, category: 'general'});

// Community nodes - create communities
CREATE (c:Community {name: 'Coffee Lovers', description: 'For coffee enthusiasts', memberCount: 0, createdAt: datetime()});
CREATE (c:Community {name: 'Outdoor Adventures', description: 'Hiking and nature lovers', memberCount: 0, createdAt: datetime()});
CREATE (c:Community {name: 'Foodies', description: 'Food and cooking enthusiasts', memberCount: 0, createdAt: datetime()});
CREATE (c:Community {name: 'Tech Enthusiasts', description: 'Technology and innovation', memberCount: 0, createdAt: datetime()});
CREATE (c:Community {name: 'Creative Arts', description: 'Artists and creatives', memberCount: 0, createdAt: datetime()});

// Relationship patterns

// 1. User likes another user
MATCH (u1:User {lineUserId: 'U1234567890abcdef'})
MATCH (u2:User {lineUserId: 'U0987654321fedcba'})
CREATE (u1)-[:LIKES {
  timestamp: datetime(),
  superLike: false
}]->(u2);

// 2. Create mutual match when both users like each other
MATCH (u1:User)-[l1:LIKES]->(u2:User)
MATCH (u2)-[l2:LIKES]->(u1)
WHERE NOT (u1)-[:MATCHES]-(u2)
CREATE (u1)-[:MATCHES {
  timestamp: datetime(),
  compatibility: 85.5,
  lastInteraction: datetime()
}]->(u2)
CREATE (u2)-[:MATCHES {
  timestamp: datetime(),
  compatibility: 85.5,
  lastInteraction: datetime()
}]->(u1);

// 3. User has interests
MATCH (u:User {lineUserId: 'U1234567890abcdef'})
MATCH (i:Interest) WHERE i.name IN u.interests
CREATE (u)-[:HAS_INTEREST {strength: 1.0}]->(i);

// 4. User joins community
MATCH (u:User {lineUserId: 'U1234567890abcdef'})
MATCH (c:Community {name: 'Coffee Lovers'})
CREATE (u)-[:IN_COMMUNITY {joinedAt: datetime(), active: true}]->(c)
SET c.memberCount = c.memberCount + 1;

// 5. Track conversations
MATCH (u1:User {lineUserId: 'U1234567890abcdef'})
MATCH (u2:User {lineUserId: 'U0987654321fedcba'})
CREATE (u1)-[:HAS_CONVERSATION {
  startedAt: datetime(),
  lastMessage: datetime(),
  messageCount: 0,
  quality: 'active'
}]->(u2);

// Useful queries for the dating system

// 1. Find potential matches for a user
MATCH (user:User {lineUserId: $userId})
MATCH (candidate:User)
WHERE candidate.lineUserId <> $userId
  AND candidate.age >= user.settings.ageRangeMin
  AND candidate.age <= user.settings.ageRangeMax
  AND user.age >= candidate.settings.ageRangeMin
  AND user.age <= candidate.settings.ageRangeMax
  AND candidate.gender = user.settings.genderPreference
  AND user.gender = candidate.settings.genderPreference
  AND distance(user.location, candidate.location) <= user.settings.maxDistance * 1000
  AND NOT (user)-[:LIKES|BLOCKS|MATCHES]-(candidate)
  AND candidate.settings.visibility = 'visible'
WITH user, candidate, distance(user.location, candidate.location) / 1000 as distanceKm
OPTIONAL MATCH (user)-[:HAS_INTEREST]->(interest)<-[:HAS_INTEREST]-(candidate)
WITH user, candidate, distanceKm, COUNT(DISTINCT interest) as sharedInterests
OPTIONAL MATCH (user)-[:IN_COMMUNITY]->(community)<-[:IN_COMMUNITY]-(candidate)
WITH user, candidate, distanceKm, sharedInterests, COUNT(DISTINCT community) as sharedCommunities
RETURN candidate {
  .*, 
  distance: distanceKm,
  sharedInterests: sharedInterests,
  sharedCommunities: sharedCommunities
}
ORDER BY sharedInterests DESC, sharedCommunities DESC, distanceKm ASC
LIMIT 20;

// 2. Get user's matches with last activity
MATCH (user:User {lineUserId: $userId})-[m:MATCHES]-(match:User)
OPTIONAL MATCH (user)-[c:HAS_CONVERSATION]-(match)
RETURN match {
  .*,
  matchedAt: m.timestamp,
  compatibility: m.compatibility,
  lastInteraction: m.lastInteraction,
  conversationStarted: c IS NOT NULL,
  messageCount: c.messageCount
}
ORDER BY m.timestamp DESC;

// 3. Get users who liked me (for premium feature)
MATCH (user:User {lineUserId: $userId})<-[l:LIKES]-(admirer:User)
WHERE NOT (user)-[:LIKES]->(admirer)
AND NOT (user)-[:BLOCKS]-(admirer)
RETURN admirer {
  .*,
  likedAt: l.timestamp,
  superLike: l.superLike
}
ORDER BY l.superLike DESC, l.timestamp DESC;

// 4. Calculate compatibility score components
MATCH (u1:User {lineUserId: $userId1})
MATCH (u2:User {lineUserId: $userId2})
// Shared interests
OPTIONAL MATCH (u1)-[:HAS_INTEREST]->(sharedInterest)<-[:HAS_INTEREST]-(u2)
WITH u1, u2, COLLECT(DISTINCT sharedInterest.name) as sharedInterests
// Shared communities
OPTIONAL MATCH (u1)-[:IN_COMMUNITY]->(sharedCommunity)<-[:IN_COMMUNITY]-(u2)
WITH u1, u2, sharedInterests, COLLECT(DISTINCT sharedCommunity.name) as sharedCommunities
// Calculate distance
WITH u1, u2, sharedInterests, sharedCommunities, 
     distance(u1.location, u2.location) / 1000 as distanceKm
RETURN {
  sharedInterests: sharedInterests,
  sharedInterestCount: SIZE(sharedInterests),
  sharedCommunities: sharedCommunities,
  sharedCommunityCount: SIZE(sharedCommunities),
  distance: distanceKm,
  ageGap: abs(u1.age - u2.age)
};

// 5. Update last active timestamp
MATCH (u:User {lineUserId: $userId})
SET u.lastActive = datetime()
RETURN u;

// 6. Get community suggestions based on interests
MATCH (u:User {lineUserId: $userId})-[:HAS_INTEREST]->(interest:Interest)
MATCH (c:Community)-[:RELATED_TO]->(interest)
WHERE NOT (u)-[:IN_COMMUNITY]->(c)
WITH c, COUNT(DISTINCT interest) as relevanceScore
RETURN c {
  .*,
  relevanceScore: relevanceScore
}
ORDER BY relevanceScore DESC
LIMIT 5;

// 7. Track user interactions for ML training
MATCH (u1:User {lineUserId: $userId1})
MATCH (u2:User {lineUserId: $userId2})
CREATE (u1)-[:VIEWED {
  timestamp: datetime(),
  duration: $duration,
  action: $action // 'like', 'pass', 'superlike'
}]->(u2);

// 8. Get dating insights for user
MATCH (u:User {lineUserId: $userId})
// Count likes given
OPTIONAL MATCH (u)-[likesGiven:LIKES]->()
WITH u, COUNT(likesGiven) as totalLikesGiven
// Count likes received
OPTIONAL MATCH (u)<-[likesReceived:LIKES]-()
WITH u, totalLikesGiven, COUNT(likesReceived) as totalLikesReceived
// Count matches
OPTIONAL MATCH (u)-[matches:MATCHES]-()
WITH u, totalLikesGiven, totalLikesReceived, COUNT(DISTINCT matches) as totalMatches
// Count conversations
OPTIONAL MATCH (u)-[convos:HAS_CONVERSATION]-()
WITH u, totalLikesGiven, totalLikesReceived, totalMatches, COUNT(DISTINCT convos) as totalConversations
RETURN {
  userId: u.lineUserId,
  memberSince: u.createdAt,
  totalLikesGiven: totalLikesGiven,
  totalLikesReceived: totalLikesReceived,
  totalMatches: totalMatches,
  totalConversations: totalConversations,
  matchRate: CASE WHEN totalLikesGiven > 0 
             THEN toFloat(totalMatches) / totalLikesGiven * 100 
             ELSE 0 END,
  conversationRate: CASE WHEN totalMatches > 0 
                    THEN toFloat(totalConversations) / totalMatches * 100 
                    ELSE 0 END
};

// 9. Cleanup old unmatched likes (housekeeping)
MATCH (u1:User)-[l:LIKES]->(u2:User)
WHERE l.timestamp < datetime() - duration('P30D') // 30 days old
AND NOT (u2)-[:LIKES]->(u1)
DELETE l;

// 10. Find users with similar taste (collaborative filtering)
MATCH (u:User {lineUserId: $userId})-[:LIKES]->(liked:User)
MATCH (similar:User)-[:LIKES]->(liked)
WHERE similar.lineUserId <> $userId
AND NOT (u)-[:LIKES|MATCHES|BLOCKS]-(similar)
WITH u, similar, COUNT(DISTINCT liked) as commonLikes
MATCH (similar)-[:LIKES]->(candidate:User)
WHERE NOT (u)-[:LIKES|MATCHES|BLOCKS]-(candidate)
AND candidate.settings.visibility = 'visible'
WITH candidate, COUNT(DISTINCT similar) as recommendationScore, 
     COLLECT(DISTINCT similar.displayName)[0..3] as recommendedBy
RETURN candidate {
  .*,
  recommendationScore: recommendationScore,
  recommendedBy: recommendedBy
}
ORDER BY recommendationScore DESC
LIMIT 10;