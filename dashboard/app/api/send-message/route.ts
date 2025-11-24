import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { to, message } = await request.json();

    if (!to || !message) {
      return NextResponse.json(
        { error: 'Missing required fields: to, message' },
        { status: 400 }
      );
    }

    // Server-side only - these are NOT exposed to the browser
    const accountSid = process.env.TWILIO_ACCOUNT_SID;
    const authToken = process.env.TWILIO_AUTH_TOKEN;
    const from = process.env.TWILIO_PHONE_NUMBER;

    if (!accountSid || !authToken || !from) {
      return NextResponse.json(
        { error: 'Twilio credentials not configured' },
        { status: 500 }
      );
    }

    // Send message via Twilio API (server-side)
    const response = await fetch(
      `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`,
      {
        method: 'POST',
        headers: {
          'Authorization': 'Basic ' + Buffer.from(`${accountSid}:${authToken}`).toString('base64'),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          To: to,
          From: from,
          Body: message,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.text();
      console.error('Twilio API error:', error);
      return NextResponse.json(
        { error: 'Failed to send message via Twilio' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Store the message in the database
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
    try {
      await fetch(`${backendUrl}/api/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone_number: to,
          direction: 'outgoing',
          message_text: message,
        }),
      });
    } catch (dbError) {
      console.error('Failed to store message in database:', dbError);
      // Don't fail the request if database storage fails - message was still sent
    }

    return NextResponse.json({ success: true, messageId: data.sid });

  } catch (error) {
    console.error('Error sending message:', error);
    return NextResponse.json(
      { error: 'Server error' },
      { status: 500 }
    );
  }
}
