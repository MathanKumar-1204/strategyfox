from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
import os
from datetime import datetime, timedelta
import json
import re
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Configure Groq API with Llama
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
groq_client = Groq(api_key=GROQ_API_KEY)

# Configure Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'src/packages.json'), 'r') as f:
    AVAILABLE_PACKAGES = json.load(f)

with open(os.path.join(BASE_DIR, 'src/attractions.json'), 'r') as f:
    AVAILABLE_ATTRACTIONS = json.load(f)
# Experience image mapping from Dashboard.jsx
EXPERIENCE_IMAGE_MAP = {
    # Thailand
    "Maya Bay": "photo-1528181304800-259b08848526",
    "Grand Palace": "photo-1590274853856-f22d5ee3d228",
    "Phi Phi Islands": "photo-1534008897995-27a23e859048",
    "Phi Phi": "photo-1534008897995-27a23e859048",
    "Dinner Cruise": "photo-1516939884455-1445c8652f83",
    "Marble Buddha & Reclining Buddha": "photo-1598902108854-10e335adac99",
    "Chao Phraya Dinner Cruise": "photo-1516939884455-1445c8652f83",
    "Mahanakhon Skywalk": "photo-1621272036047-bb0f76bbc1ad",
    "Safari World & Marine Park": "photo-1708876543795-5581bbdf1d28",
    "James Bond Island": "photo-1528181304800-259b08848526",
    "ATV and River Rafting": "photo-1744472679343-9d2666c9ffc9",
    "Carnival Magic / Phuket Fantasea": "photo-1638287527782-56569934c034",
    "Tiger Kingdom Encounter": "photo-1477764250597-dffe9f601ae8",
    "Alcazar Show": "photo-1508612761958-e931d843bdd5",
    "Sanctuary of Truth": "photo-1644902617098-45abe72a7445",
    "Coral Island": "photo-1544644181-1484b3fdfc62",
    "Noong Nooch Village & Garden": "photo-1598970434795-0c54fe7c0648",
    "Yacht / Pool Party": "photo-1534190760961-74e8c1c5c3da",
    # Vietnam
    "Luxury Halong Cruise": "photo-1528127269322-539801943592",
    "Hanoi Old Quarter": "photo-1555939594-58d7cb561ad1",
    "Authentic Pho Tasting": "photo-1582878826629-29b7ad1cdc43",
    # Bali
    "Tegallalang Rice Terrace": "photo-1536431311719-398b6704d4cc",
    "Kelingking Beach": "photo-1555400038-63f5ba517a47",
    "Uluwatu Dance": "photo-1518548419970-58e3b4079ab2",
    "Jungle Villas": "photo-1668854085665-0eed599e8078",
    # Maldives
    "Overwater Villa": "photo-1514282401047-d79a71a590e8",
    "Sea Plane Transfer": "photo-1512100356356-de1b84283e18",
    "Private Sandbank Dinner": "photo-1746138394984-5691db44df00",
    # Hong Kong
    "Victoria Peak": "photo-1506461883276-594a12b11cf3",
    "HK Disneyland": "photo-1737040009019-1576b1342b0e",
    "Big Buddha": "photo-1513415564515-763d91423bdd",
    "Symphony of Lights": "photo-1506461883276-594a12b11cf3",
    # Malaysia
    "Petronas Twin Towers": "photo-1532442782935-dc7ee648a2a5",
    "Langkawi Sky Bridge": "photo-1669812849320-283db1bf8216",
    "Batu Caves": "photo-1563811771046-ba984ff30900",
}

FALLBACK_POOL = [
    "photo-1507525428034-b723cf961d3e",  # Beach
    "photo-1449034446853-66c86144b0ad",  # City
    "photo-1540541338287-41700207dee6",  # Resort
    "photo-1441974231531-c6227db76b6e",  # Forest
    "photo-1436491865332-7a61a109c055",  # Plane
    "photo-1501785888041-af3ef285b470",  # Sunset
    "photo-1470225620780-dba8ba36b745",  # Nightlife
    "photo-1534447677768-be436bb09401",  # Boat
    "photo-1566073771259-6a8506099945",  # Luxury
    "photo-1508921912186-1d1395ee5575",  # Temple
    "photo-1476514525535-07fb3b4ae5f1",  # Landscape
]

COLOR_THEMES = [
    {"bg": "#EFEAFF", "border": "#D3C4FF", "text": "#5D3EB0", "icon": "#7856D3"},
    {"bg": "#E6F8ED", "border": "#BBE6CE", "text": "#197741", "icon": "#279A58"},
    {"bg": "#EBF4FF", "border": "#BEDAFF", "text": "#1D62B5", "icon": "#2B7DD8"},
    {"bg": "#FFEBEA", "border": "#FFC4C2", "text": "#BC2A25", "icon": "#DD433D"},
    {"bg": "#FFF4E5", "border": "#FFDDB3", "text": "#A85E00", "icon": "#D67D00"},
]

def get_image_for_experience(experience_name, index=0):
    """Get image URL for an experience, matching Dashboard.jsx logic"""
    photo_id = EXPERIENCE_IMAGE_MAP.get(experience_name)
    
    if not photo_id:
        for key in EXPERIENCE_IMAGE_MAP:
            if experience_name.lower() in key.lower() or key.lower() in experience_name.lower():
                photo_id = EXPERIENCE_IMAGE_MAP[key]
                break
    
    if not photo_id:
        photo_id = FALLBACK_POOL[(index + len(experience_name)) % len(FALLBACK_POOL)]
    
    return f"https://images.unsplash.com/{photo_id}?q=80&w=600&auto=format&fit=crop"

def get_groq_response(prompt):
    """Get response from Groq Llama model"""
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful travel planning assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq API Error: {e}")
        # Fallback to smaller model
        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful travel planning assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e2:
            print(f"Groq API Error with fallback: {e2}")
            return None
@app.route('/')
def index():
    return "Hello, World!"
@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages for trip planning"""
    try:
        data = request.json
        user_message = data.get('message', '')
        chat_history = data.get('history', [])
        user_id = data.get('userId')  # Get user ID from frontend
        
        # System prompt for trip planning assistant
        system_prompt = """You are Honey, a friendly and fun travel planning assistant for Honey Vacations. 
Your goal is to help users plan their perfect trip by asking engaging questions.

You need to collect these details:
1. Destination (where they want to go)
2. Number of travelers (adults and children)
3. Travel dates (start date and end date, or number of days)
4. Budget (total or per person)
5. Travel style (adventure, exotic/relaxation, family-friendly with children, cultural, romantic)

Guidelines:
- Be friendly, enthusiastic, and use emojis occasionally
- Ask ONE question at a time in a conversational way
- Make it fun and engaging, like talking to a travel-savvy friend
- Use phrases like "Amazing choice!", "That sounds wonderful!", "Great pick!"
- For families with kids, suggest family-friendly activities
- For adventure lovers, suggest exciting experiences
- For exotic/relaxation, suggest peaceful, luxurious experiences
- Keep responses concise (2-4 sentences max)
- When you have ALL the information, respond with ONLY this exact message (NO JSON, NO extra text):
COMPLETE_TRIP_DATA

Do NOT output JSON or any data structure. Just output the text: COMPLETE_TRIP_DATA"""

        # Build conversation history
        messages = [system_prompt]
        for msg in chat_history:
            messages.append(f"{msg['role']}: {msg['content']}")
        messages.append(f"user: {user_message}")
        
        prompt = "\n".join(messages)
        
        # Get Groq Llama response
        response = get_groq_response(prompt)
        
        if response:
            # Check if trip is complete
            if 'COMPLETE_TRIP_DATA' in response or 'complete' in response.lower() or '{"complete": true' in response:
                print("\n🎯 Trip data collection complete!")
                print(f"📋 Chat history length: {len(chat_history)}")
                
                # Extract trip data from conversation history
                trip_data = extract_trip_data_from_history(chat_history)
                
                if trip_data:
                    print(f"✅ Extracted trip data: {json.dumps(trip_data, indent=2)}")
                    
                    if user_id:
                        print(f"👤 User ID: {user_id}")
                        print("🚀 Creating AI plan...")
                        
                        # Automatically create and save the plan
                        plan_result = create_ai_plan(user_id, trip_data)
                        
                        if plan_result['success']:
                            print(f"✅ Plan created successfully with ID: {plan_result['planId']}")
                            return jsonify({
                                'success': True,
                                'complete': True,
                                'data': trip_data,
                                'planId': plan_result['planId'],
                                'message': f"Perfect! I've created your dream itinerary and saved it to your profile! 🎉 You can view and edit it anytime."
                            })
                        else:
                            print(f"❌ Plan creation failed: {plan_result.get('message')}")
                    else:
                        print("⚠️ No user ID provided")
                else:
                    print("❌ Failed to extract trip data from history")
                
                # Fallback if extraction fails
                return jsonify({
                    'success': True,
                    'complete': True,
                    'data': trip_data,
                    'message': response if 'COMPLETE_TRIP_DATA' not in response else "Perfect! I have everything I need. Let me create your dream itinerary!"
                })
            
            return jsonify({
                'success': True,
                'complete': False,
                'message': response
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Sorry, I\'m having trouble responding right now. Please try again!'
            }), 500
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again!'
        }), 500

def extract_trip_data_from_history(chat_history):
    """Extract trip data from conversation history"""
    print("\n🔍 Extracting trip data from chat history...")
    
    trip_data = {
        'destination': None,
        'travelers': {'adults': 1, 'children': 0},
        'startDate': None,
        'endDate': None,
        'budget': None,
        'travelStyle': None
    }
    
    # Parse through conversation to extract information
    for msg in chat_history:
        content = msg.get('content', '').lower()
        
        # Extract destination
        if trip_data['destination'] is None:
            # Look for destination mentions
            dest_keywords = ['thailand', 'vietnam', 'bali', 'maldives', 'hong kong', 'malaysia', 'bangkok', 'phuket', 'pattaya', 'singapore']
            for dest in dest_keywords:
                if dest in content:
                    trip_data['destination'] = dest.title()
                    print(f"  📍 Found destination: {trip_data['destination']}")
                    break
        
        # Extract travelers
        if 'adult' in content or 'adults' in content:
            numbers = re.findall(r'(\d+)\s*adults?', content)
            if numbers:
                trip_data['travelers']['adults'] = int(numbers[0])
                print(f"  👥 Found adults: {trip_data['travelers']['adults']}")
        
        if 'child' in content or 'children' in content or 'kid' in content or 'kids' in content:
            numbers = re.findall(r'(\d+)\s*(?:children|kids|child)', content)
            if numbers:
                trip_data['travelers']['children'] = int(numbers[0])
                print(f"  👶 Found children: {trip_data['travelers']['children']}")
        
        # Extract dates (look for date patterns)
        date_patterns = re.findall(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', content)
        if date_patterns and not trip_data['startDate']:
            first_date = date_patterns[0]
            day, month, year = first_date
            if len(year) == 2:
                year = f'20{year}'
            trip_data['startDate'] = f'{year}-{month.zfill(2)}-{day.zfill(2)}'
            print(f"  📅 Found start date: {trip_data['startDate']}")
            
            if len(date_patterns) > 1:
                second_date = date_patterns[1]
                day, month, year = second_date
                if len(year) == 2:
                    year = f'20{year}'
                trip_data['endDate'] = f'{year}-{month.zfill(2)}-{day.zfill(2)}'
                print(f"  📅 Found end date: {trip_data['endDate']}")
        
        # Extract budget
        budget_keywords = ['low', 'budget', 'economy', 'medium', 'moderate', 'high', 'luxury', 'premium']
        for budget in budget_keywords:
            if budget in content:
                trip_data['budget'] = budget
                print(f"  💰 Found budget: {trip_data['budget']}")
                break
        
        # Extract travel style
        style_keywords = ['adventure', 'adventurous', 'relax', 'relaxation', 'exotic', 'family', 'cultural', 'romantic', 'romance']
        for style in style_keywords:
            if style in content:
                if 'adventur' in style:
                    trip_data['travelStyle'] = 'adventure'
                elif 'relax' in style or 'exotic' in style:
                    trip_data['travelStyle'] = 'relaxation'
                elif 'family' in style:
                    trip_data['travelStyle'] = 'family'
                elif 'cultural' in style:
                    trip_data['travelStyle'] = 'cultural'
                elif 'romantic' in style or 'romance' in style:
                    trip_data['travelStyle'] = 'romantic'
                print(f"  🎯 Found travel style: {trip_data['travelStyle']}")
                break
    
    # Return None if essential data is missing
    if not trip_data['destination'] or not trip_data['startDate'] or not trip_data['endDate']:
        print(f"❌ Missing essential data - Destination: {trip_data['destination']}, Start: {trip_data['startDate']}, End: {trip_data['endDate']}")
        return None
    
    print("✅ Trip data extraction complete!")
    return trip_data


def find_matching_package(destination, travel_style):
    """Find the best matching package from available packages and attractions"""
    destination_lower = destination.lower()
    
    # First, search for matching packages based on destination
    for package in AVAILABLE_PACKAGES:
        package_locations = [loc.lower() for loc in package.get('locations', [])]
        package_name_lower = package.get('name', '').lower()
        package_category = package.get('category', '').lower()
        
        # Check if destination matches any location or package name
        if (destination_lower in package_locations or 
            destination_lower in package_name_lower or
            any(loc in destination_lower for loc in package_locations) or
            any(dest in package_name_lower for dest in destination_lower.split())):
            return package
    
    # If no package match, check attractions data for destination
    for attraction in AVAILABLE_ATTRACTIONS:
        attraction_location = attraction.get('location', '').lower()
        attraction_name = attraction.get('name', '').lower()
        
        if (destination_lower in attraction_location or
            destination_lower in attraction_name or
            attraction_location in destination_lower):
            # Found matching attraction, return a custom package based on it
            return {
                'id': f"custom-{destination_lower.replace(' ', '-')}",
                'name': f"{destination.title()} Experience",
                'package_name': f"Custom {destination.title()} Tour",
                'duration': 'Custom',
                'category': travel_style.title() if travel_style else 'Custom',
                'itinerary': [],
                'highlights': [attraction.get('name', '')],
                'description': f"Custom itinerary for {destination}",
                'locations': [attraction.get('location', '')]
            }
    
    # If no match at all, return None and let AI generate custom itinerary
    return None


def generate_custom_itinerary(trip_data):
    """Generate a custom itinerary using Gemini AI based on available package and attraction data"""
    # Provide packages and attractions as reference
    packages_info = json.dumps(AVAILABLE_PACKAGES[:3], indent=2)  # First 3 packages as example
    attractions_info = json.dumps(AVAILABLE_ATTRACTIONS, indent=2)  # All attractions
    
    prompt = f"""Create a detailed day-by-day travel itinerary in JSON format based on these trip details:
- Destination: {trip_data.get('destination')}
- Travelers: {trip_data.get('travelers', {}).get('adults', 1)} adults, {trip_data.get('travelers', {}).get('children', 0)} children
- Dates: {trip_data.get('startDate')} to {trip_data.get('endDate')}
- Budget: {trip_data.get('budget')}
- Travel Style: {trip_data.get('travelStyle')}

Here are the available packages from our app for reference:
{packages_info}

Here are the available attractions from our app:
{attractions_info}

Create a structured itinerary using ONLY the attractions and experiences from the data above. The itinerary should be a JSON object with this exact format:
{{
  "itinerary": [
    {{
      "day": 1,
      "title": "Day title",
      "description": "Detailed description including attraction names from the data above"
    }}
  ],
  "highlights": ["Highlight 1", "Highlight 2"],
  "locations": ["Location 1", "Location 2"]
}}

IMPORTANT:
- Use attraction names and package experiences from the provided data
- Match the destination to available packages/attractions
- Make it engaging and personalized to their travel style
- Return ONLY the JSON object, no extra text"""
    
    response = get_groq_response(prompt)
    
    if response:
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    
    return None


def create_plan_events(itinerary, start_date, total_days, package_name=''):
    """Convert itinerary to plan events format matching Dashboard.jsx structure"""
    import random
    events = []
    event_index = 0
    
    for day_plan in itinerary:
        day = day_plan.get('day', 1)
        title = day_plan.get('title', f'Day {day}')
        description = day_plan.get('description', '')
        
        # Generate unique event ID like Dashboard: evt_timestamp_randomstring
        import time
        event_id = f"evt_{int(time.time() * 1000)}_{''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=5))}"
        
        # Get image for this experience
        image_url = get_image_for_experience(title, event_index)
        
        # Random time slot (morning 9-11 AM or afternoon 2-4 PM)
        hour = random.choice([9, 10, 11, 14, 15, 16])
        duration = random.choice([3, 4, 5])
        
        # Format startTime like Dashboard: "03:00 PM"
        if hour >= 12:
            display_hour = hour - 12 if hour > 12 else 12
            start_time = f"{display_hour:02d}:00 PM"
        else:
            start_time = f"{hour:02d}:00 AM"
        
        # Random color theme from Dashboard's colorMap
        color_theme = random.choice(COLOR_THEMES)
        
        # Create event matching Dashboard.jsx format exactly
        events.append({
            'id': event_id,
            'day': day,
            'hour': hour,
            'type': 'experience',
            'image': image_url,
            'title': title,
            'duration': duration,
            'location': package_name,
            'startTime': start_time,
            'colorTheme': color_theme,
            'description': description if description else f'Explore the unique wonders and authentic experiences found only in {title}.'
        })
        
        event_index += 1
    
    print(f"📋 Created {len(events)} timeline events")
    return events


def create_ai_plan(user_id, trip_data):
    """Create and save AI-generated plan to Supabase using app's package and attraction data"""
    try:
        # Calculate total days
        start_date = datetime.strptime(trip_data.get('startDate'), '%Y-%m-%d')
        end_date = datetime.strptime(trip_data.get('endDate'), '%Y-%m-%d')
        total_days = (end_date - start_date).days + 1
        
        # Find matching package (checks both packages.json and attractions.json)
        matching_package = find_matching_package(
            trip_data.get('destination'),
            trip_data.get('travelStyle')
        )
        
        itinerary_data = None
        package_name = ''
        
        if matching_package and matching_package.get('itinerary'):
            # Use existing package itinerary data
            print(f"✅ Using package: {matching_package.get('name')}")
            itinerary_data = matching_package.get('itinerary', [])
            package_name = matching_package.get('package_name', '')
        elif matching_package:
            # Package found but no itinerary, generate custom using AI
            print(f"🤖 Generating custom itinerary for: {trip_data.get('destination')}")
            itinerary_data = generate_custom_itinerary(trip_data)
            if itinerary_data:
                itinerary_data = itinerary_data.get('itinerary', [])
                package_name = matching_package.get('package_name', f"Custom {trip_data.get('destination')} Tour")
            else:
                # Fallback: create simple itinerary
                itinerary_data = [
                    {
                        'day': day,
                        'title': f'Day {day} - Explore {trip_data.get("destination")}',
                        'description': f'Enjoy your time exploring {trip_data.get("destination")} and experiencing local culture.'
                    }
                    for day in range(1, total_days + 1)
                ]
                package_name = f"{trip_data.get('destination')} Adventure"
        else:
            # No matching package, generate completely custom itinerary using AI
            print(f"🎨 Creating custom AI itinerary for: {trip_data.get('destination')}")
            itinerary_data = generate_custom_itinerary(trip_data)
            if itinerary_data:
                itinerary_data = itinerary_data.get('itinerary', [])
                package_name = f"Custom {trip_data.get('destination')} Tour"
            else:
                # Ultimate fallback
                itinerary_data = [
                    {
                        'day': day,
                        'title': f'Day {day} - {trip_data.get("destination")}',
                        'description': f'Discover amazing attractions and experiences in {trip_data.get("destination")}.'
                    }
                    for day in range(1, total_days + 1)
                ]
                package_name = f"{trip_data.get('destination')} Experience"
        
        print(f"📋 Generated {len(itinerary_data)} day itinerary")
        
        # Create plan events from itinerary (passing package_name for location field)
        timeline = create_plan_events(itinerary_data, trip_data.get('startDate'), total_days, package_name)
        
        # Create plan object
        plan = {
            'user_id': user_id,
            'trip_name': f"AI-Planned: {trip_data.get('destination')}",
            'destination': trip_data.get('destination'),
            'start_date': trip_data.get('startDate'),
            'end_date': trip_data.get('endDate'),
            'total_days': total_days,
            'arrival_hour': 9,
            'departure_hour': 18,
            'timeline': timeline,
            'package_name': package_name,
            'created_by': 'ai',
            'is_ai_generated': True
        }
        
        # Save to Supabase
        result = supabase.table('plans').insert(plan).execute()
        
        if result.data:
            plan_id = result.data[0]['id']
            print(f"✅ Plan saved successfully with ID: {plan_id}")
            return {
                'success': True,
                'planId': plan_id,
                'message': 'Plan created and saved successfully'
            }
        else:
            print(f"❌ Failed to save plan: {result}")
            return {
                'success': False,
                'message': 'Failed to save plan to database'
            }
            
    except Exception as e:
        print(f"❌ Error creating AI plan: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e)
        }


@app.route('/api/generate-itinerary', methods=['POST'])
def generate_itinerary():
    """Generate a detailed itinerary based on trip details"""
    try:
        data = request.json
        
        prompt = f"""Create a detailed day-by-day travel itinerary with the following details:
- Destination: {data.get('destination')}
- Travelers: {data.get('travelers')} adults, {data.get('children', 0)} children
- Dates: {data.get('startDate')} to {data.get('endDate')}
- Budget: {data.get('budget')}
- Travel Style: {data.get('travelStyle')}

Provide a structured response with:
1. Day-wise activities and attractions
2. Estimated costs per day
3. Recommended hotels/accommodations
4. Travel tips and recommendations
5. Must-try local food

Make it engaging and personalized to their travel style."""
        
        response = get_groq_response(prompt)
        
        if response:
            return jsonify({
                'success': True,
                'itinerary': response
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate itinerary'
            }), 500
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500

if __name__ == '__main__':
    print("🚀 Honey Vacations AI Assistant API starting...")
    print("📍 Running on: http://localhost:5000")
    app.run(debug=True, port=5000)
