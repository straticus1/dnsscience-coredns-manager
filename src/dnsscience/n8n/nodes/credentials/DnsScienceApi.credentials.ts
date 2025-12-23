import {
	ICredentialType,
	INodeProperties,
} from 'n8n-workflow';

export class DnsScienceApi implements ICredentialType {
	name = 'dnsScienceApi';
	displayName = 'DNS Science API';
	documentationUrl = 'https://docs.dnsscience.io/api';

	properties: INodeProperties[] = [
		{
			displayName: 'API URL',
			name: 'apiUrl',
			type: 'string',
			default: 'http://localhost:8080',
			placeholder: 'http://dnsscience-api:8080',
			description: 'The URL of the DNS Science Toolkit API',
		},
		{
			displayName: 'API Key',
			name: 'apiKey',
			type: 'string',
			typeOptions: {
				password: true,
			},
			default: '',
			description: 'API key for authentication (optional)',
		},
		{
			displayName: 'Target Resolver',
			name: 'defaultResolver',
			type: 'options',
			options: [
				{
					name: 'CoreDNS',
					value: 'coredns',
				},
				{
					name: 'Unbound',
					value: 'unbound',
				},
			],
			default: 'coredns',
			description: 'Default DNS resolver to manage',
		},
	];
}
